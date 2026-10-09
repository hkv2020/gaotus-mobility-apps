import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:image_picker/image_picker.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/booking.dart';
import '../models/operation_stop.dart';
import '../state/app_session.dart';
import 'chat_screen.dart';

class OperationsJobScreen extends StatelessWidget {
  const OperationsJobScreen({super.key, required this.session});

  final AppSession session;

  Future<void> _navigate(BuildContext context, OperationStop stop) async {
    final destination = stop.lat != null && stop.lng != null
        ? '${stop.lat},${stop.lng}'
        : Uri.encodeComponent(stop.address);
    final uri = Uri.parse('https://www.google.com/maps/dir/?api=1&destination=$destination&travelmode=driving');
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not open navigation.')));
    }
  }

  Future<void> _call(BuildContext context, String phone) async {
    if (phone.trim().isEmpty) return;
    final uri = Uri(scheme: 'tel', path: phone.trim());
    if (!await launchUrl(uri) && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not open the phone app.')));
    }
  }

  Future<void> _setStopStatus(BuildContext context, OperationStop stop, String status,
      {Map<String, Object?> proof = const <String, Object?>{}}) async {
    try {
      await session.updateOperationStopStatus(stop.id, status, proof: proof);
      if (!context.mounted) return;
      final job = session.currentJob;
      if (job == null || job.status == 'completed') {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Operations job completed.')));
        if (Navigator.of(context).canPop()) Navigator.of(context).pop();
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(session.errorMessage ?? 'Could not update stop.')),
        );
      }
    }
  }

  Future<void> _completeStop(BuildContext context, Booking job, OperationStop stop) async {
    final proof = await showModalBottomSheet<Map<String, Object?>>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _ProofOfDeliverySheet(stop: stop, settings: job.podSettings),
    );
    if (proof == null || !context.mounted) return;
    await _setStopStatus(context, stop, 'completed', proof: proof);
  }

  Future<void> _exceptionStop(BuildContext context, OperationStop stop, String status) async {
    final controller = TextEditingController();
    final label = status == 'failed' ? 'Failed delivery / collection' : 'Postpone stop';
    final reason = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(label),
        content: TextField(
          controller: controller,
          autofocus: true,
          minLines: 2,
          maxLines: 4,
          decoration: const InputDecoration(labelText: 'Reason', hintText: 'Customer unavailable, access issue…'),
        ),
        actions: <Widget>[
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(), child: const Text('Cancel')),
          FilledButton(
            onPressed: () {
              final value = controller.text.trim();
              if (value.isNotEmpty) Navigator.of(dialogContext).pop(value);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (reason == null || !context.mounted) return;
    await _setStopStatus(context, stop, status, proof: <String, Object?>{'failure_reason': reason});
  }

  Color _statusColor(String status) => switch (status) {
        'completed' => const Color(0xFF0B8F55),
        'failed' => const Color(0xFFC43131),
        'postponed' => const Color(0xFFE38B00),
        'arrived' => const Color(0xFF7A4CE0),
        'enroute' => const Color(0xFF276EF1),
        _ => const Color(0xFF5E6670),
      };

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: session,
      builder: (context, _) {
        final job = session.currentJob;
        if (job == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Operations job')),
            body: const Center(child: Text('No active operations job.')),
          );
        }
        final next = job.nextOperationStop;
        final points = <LatLng>[
          for (final stop in job.stops)
            if (stop.lat != null && stop.lng != null && !stop.isTerminal) LatLng(stop.lat!, stop.lng!),
          if (session.lastPosition != null) LatLng(session.lastPosition!.latitude, session.lastPosition!.longitude),
        ];
        final center = next?.lat != null && next?.lng != null
            ? LatLng(next!.lat!, next.lng!)
            : points.isNotEmpty
                ? points.first
                : const LatLng(51.5074, -0.1278);

        final markers = <Marker>[
          for (final stop in job.stops)
            if (stop.lat != null && stop.lng != null)
              Marker(
                point: LatLng(stop.lat!, stop.lng!),
                width: 42,
                height: 42,
                child: _NumberedStopMarker(
                  number: stop.sequence,
                  color: _statusColor(stop.status),
                  selected: next?.id == stop.id,
                ),
              ),
          if (session.lastPosition != null)
            Marker(
              point: LatLng(session.lastPosition!.latitude, session.lastPosition!.longitude),
              width: 48,
              height: 48,
              child: const _DriverMarker(),
            ),
        ];

        final summary = job.operationsSummary;
        return Scaffold(
          appBar: AppBar(
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(job.jobTypeLabel, style: const TextStyle(fontWeight: FontWeight.w900)),
                Text('Job #${job.id} · ${summary.completed}/${summary.total} stops', style: const TextStyle(fontSize: 12)),
              ],
            ),
            actions: <Widget>[
              IconButton(
                tooltip: 'Chat',
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(builder: (_) => ChatScreen(session: session, bookingId: job.id)),
                ),
                icon: const Icon(Icons.chat_bubble_outline_rounded),
              ),
              IconButton(
                tooltip: 'Refresh',
                onPressed: session.busy ? null : () => session.refreshOperationsJob(silent: false),
                icon: const Icon(Icons.refresh_rounded),
              ),
            ],
          ),
          body: Column(
            children: <Widget>[
              SizedBox(
                height: MediaQuery.sizeOf(context).height * .38,
                child: FlutterMap(
                  options: MapOptions(
                    initialCenter: center,
                    initialZoom: 13.5,
                    initialCameraFit: points.length >= 2
                        ? CameraFit.bounds(bounds: LatLngBounds.fromPoints(points), padding: const EdgeInsets.all(42))
                        : null,
                  ),
                  children: <Widget>[
                    TileLayer(
                      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'ai.gaotus.gaotus_mobility_driver',
                    ),
                    MarkerLayer(markers: markers),
                  ],
                ),
              ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: () => session.refreshOperationsJob(silent: false),
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
                    children: <Widget>[
                      _ProgressHeader(job: job),
                      const SizedBox(height: 16),
                      if (next != null)
                        _NextStopCard(
                          stop: next,
                          disabled: session.busy,
                          onNavigate: () => _navigate(context, next),
                          onCall: next.primaryPhone.isEmpty ? null : () => _call(context, next.primaryPhone),
                          onAdvance: () {
                            final status = switch (next.status) {
                              'pending' || 'assigned' => 'enroute',
                              'enroute' => 'arrived',
                              _ => '',
                            };
                            if (status.isNotEmpty) _setStopStatus(context, next, status);
                          },
                          onComplete: () => _completeStop(context, job, next),
                          onFailed: () => _exceptionStop(context, next, 'failed'),
                          onPostpone: () => _exceptionStop(context, next, 'postponed'),
                        )
                      else
                        const _AllStopsDoneCard(),
                      const SizedBox(height: 20),
                      Text('Route stops', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900)),
                      const SizedBox(height: 10),
                      ...job.stops.map((stop) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: _StopListTile(
                              stop: stop,
                              selected: next?.id == stop.id,
                              color: _statusColor(stop.status),
                            ),
                          )),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ProgressHeader extends StatelessWidget {
  const _ProgressHeader({required this.job});
  final Booking job;

  @override
  Widget build(BuildContext context) {
    final summary = job.operationsSummary;
    final progress = summary.total <= 0 ? 0.0 : summary.completed / summary.total;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: const Color(0xFF111111), borderRadius: BorderRadius.circular(22)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(children: <Widget>[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(99)),
              child: Text(job.jobTypeLabel.toUpperCase(), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900)),
            ),
            const Spacer(),
            Text('${summary.completed}/${summary.total}', style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
          ]),
          const SizedBox(height: 12),
          LinearProgressIndicator(value: progress.clamp(0, 1), minHeight: 8, borderRadius: BorderRadius.circular(99)),
          const SizedBox(height: 9),
          Text(
            '${summary.pending + summary.active} remaining · ${summary.failed} failed · ${summary.postponed} postponed',
            style: const TextStyle(color: Color(0xFFC9CED5), fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _NextStopCard extends StatelessWidget {
  const _NextStopCard({
    required this.stop,
    required this.disabled,
    required this.onNavigate,
    required this.onCall,
    required this.onAdvance,
    required this.onComplete,
    required this.onFailed,
    required this.onPostpone,
  });

  final OperationStop stop;
  final bool disabled;
  final VoidCallback onNavigate;
  final VoidCallback? onCall;
  final VoidCallback onAdvance;
  final VoidCallback onComplete;
  final VoidCallback onFailed;
  final VoidCallback onPostpone;

  @override
  Widget build(BuildContext context) {
    final arrived = stop.status == 'arrived';
    final actionLabel = switch (stop.status) {
      'pending' || 'assigned' => 'Start route to stop',
      'enroute' => 'I’ve arrived',
      _ => '',
    };
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(color: const Color(0xFFF4F6F8), borderRadius: BorderRadius.circular(24)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(children: <Widget>[
            CircleAvatar(
              backgroundColor: Colors.black,
              foregroundColor: Colors.white,
              child: Text('${stop.sequence}', style: const TextStyle(fontWeight: FontWeight.w900)),
            ),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text('Next · ${stop.operationLabel}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18)),
              Text(stop.status.toUpperCase(), style: const TextStyle(color: Color(0xFF69717C), fontWeight: FontWeight.w800, fontSize: 11, letterSpacing: .7)),
            ])),
          ]),
          const SizedBox(height: 14),
          Text(stop.address.isEmpty ? 'Address unavailable' : stop.address, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, height: 1.25)),
          if (stop.primaryContactName.isNotEmpty) ...<Widget>[
            const SizedBox(height: 7),
            Text(stop.primaryContactName, style: const TextStyle(fontWeight: FontWeight.w700)),
          ],
          if (stop.timeWindowStart.isNotEmpty || stop.timeWindowEnd.isNotEmpty) ...<Widget>[
            const SizedBox(height: 7),
            Text('Window: ${stop.timeWindowStart}${stop.timeWindowEnd.isEmpty ? '' : ' – ${stop.timeWindowEnd}'}'),
          ],
          if (stop.packageRef.isNotEmpty || stop.packageCount > 0 || stop.packageWeightKg > 0) ...<Widget>[
            const SizedBox(height: 10),
            Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
              if (stop.packageRef.isNotEmpty) _Chip(text: 'Ref ${stop.packageRef}'),
              if (stop.packageCount > 0) _Chip(text: '${stop.packageCount} package${stop.packageCount == 1 ? '' : 's'}'),
              if (stop.packageWeightKg > 0) _Chip(text: '${stop.packageWeightKg.toStringAsFixed(1)} kg'),
              if (stop.codAmount > 0) _Chip(text: 'COD £${stop.codAmount.toStringAsFixed(2)}'),
            ]),
          ],
          if (stop.driverInstructions.isNotEmpty || stop.notes.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Text([stop.driverInstructions, stop.notes].where((e) => e.trim().isNotEmpty).join('\n'), style: const TextStyle(color: Color(0xFF4E5661), height: 1.35)),
          ],
          const SizedBox(height: 16),
          Row(children: <Widget>[
            Expanded(child: OutlinedButton.icon(onPressed: disabled ? null : onNavigate, icon: const Icon(Icons.navigation_rounded), label: const Text('Navigate'))),
            if (onCall != null) ...<Widget>[
              const SizedBox(width: 8),
              IconButton.filledTonal(onPressed: disabled ? null : onCall, icon: const Icon(Icons.call_rounded)),
            ],
          ]),
          const SizedBox(height: 10),
          if (!arrived && actionLabel.isNotEmpty)
            FilledButton(onPressed: disabled ? null : onAdvance, child: Text(actionLabel))
          else if (arrived) ...<Widget>[
            FilledButton.icon(onPressed: disabled ? null : onComplete, icon: const Icon(Icons.verified_rounded), label: const Text('Complete with proof')),
            const SizedBox(height: 8),
            Row(children: <Widget>[
              Expanded(child: OutlinedButton(onPressed: disabled ? null : onFailed, child: const Text('Failed'))),
              const SizedBox(width: 8),
              Expanded(child: OutlinedButton(onPressed: disabled ? null : onPostpone, child: const Text('Postpone'))),
            ]),
          ],
        ],
      ),
    );
  }
}

class _ProofOfDeliverySheet extends StatefulWidget {
  const _ProofOfDeliverySheet({required this.stop, required this.settings});
  final OperationStop stop;
  final OperationsPodSettings settings;

  @override
  State<_ProofOfDeliverySheet> createState() => _ProofOfDeliverySheetState();
}

class _ProofOfDeliverySheetState extends State<_ProofOfDeliverySheet> {
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _recipient = TextEditingController();
  final TextEditingController _pin = TextEditingController();
  final TextEditingController _barcode = TextEditingController();
  final TextEditingController _packageCount = TextEditingController();
  final TextEditingController _note = TextEditingController();
  final GlobalKey _signatureKey = GlobalKey();
  final List<Offset?> _signaturePoints = <Offset?>[];
  Uint8List? _photoBytes;
  String? _photoDataUrl;
  bool _submitting = false;

  OperationsPodSettings get settings => widget.settings;

  bool get _photoRequired {
    if (widget.stop.isDelivery) return settings.requirePhotoDelivery;
    if (widget.stop.isPickup) return settings.requirePhotoPickup;
    return false;
  }

  @override
  void initState() {
    super.initState();
    _recipient.text = widget.stop.recipientName;
    if (widget.stop.packageCount > 0) _packageCount.text = '${widget.stop.packageCount}';
  }

  @override
  void dispose() {
    _recipient.dispose();
    _pin.dispose();
    _barcode.dispose();
    _packageCount.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _capturePhoto() async {
    final image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 72,
      maxWidth: 1600,
      maxHeight: 1600,
      requestFullMetadata: false,
    );
    if (image == null) return;
    final bytes = await image.readAsBytes();
    if (!mounted) return;
    setState(() {
      _photoBytes = bytes;
      _photoDataUrl = 'data:image/jpeg;base64,${base64Encode(bytes)}';
    });
  }

  Future<String?> _signatureDataUrl() async {
    if (_signaturePoints.whereType<Offset>().length < 2) return null;
    final boundary = _signatureKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
    if (boundary == null) return null;
    final image = await boundary.toImage(pixelRatio: 2);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    if (data == null) return null;
    return 'data:image/png;base64,${base64Encode(data.buffer.asUint8List())}';
  }

  Future<void> _submit() async {
    if (_photoRequired && _photoDataUrl == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Take a proof photo before completing this stop.')));
      return;
    }
    if (settings.requireRecipientName && _recipient.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Recipient name is required.')));
      return;
    }
    if (settings.requirePin && _pin.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Confirmation PIN is required.')));
      return;
    }
    if (settings.requireBarcode && _barcode.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Barcode / reference is required.')));
      return;
    }
    if (settings.requireSignature && _signaturePoints.whereType<Offset>().length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Recipient signature is required.')));
      return;
    }
    setState(() => _submitting = true);
    final signature = settings.enableSignature ? await _signatureDataUrl() : null;
    if (!mounted) return;
    final proof = <String, Object?>{
      if (_photoDataUrl != null) 'photo_base64': _photoDataUrl,
      if (signature != null) 'signature_base64': signature,
      if (_recipient.text.trim().isNotEmpty) 'recipient_name': _recipient.text.trim(),
      if (_pin.text.trim().isNotEmpty) 'pin': _pin.text.trim(),
      if (_barcode.text.trim().isNotEmpty) 'barcode': _barcode.text.trim(),
      if (_packageCount.text.trim().isNotEmpty) 'package_count': int.tryParse(_packageCount.text.trim()) ?? 0,
      if (_note.text.trim().isNotEmpty) 'note': _note.text.trim(),
    };
    Navigator.of(context).pop(proof);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(30))),
      padding: EdgeInsets.fromLTRB(18, 12, 18, 18 + MediaQuery.viewInsetsOf(context).bottom + MediaQuery.paddingOf(context).bottom),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Center(child: Container(width: 44, height: 5, decoration: BoxDecoration(color: const Color(0xFFD5D5D5), borderRadius: BorderRadius.circular(99)))),
            const SizedBox(height: 16),
            const Text('Proof of completion', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
            const SizedBox(height: 4),
            Text('${widget.stop.operationLabel} · stop ${widget.stop.sequence}', style: const TextStyle(color: Color(0xFF666666))),
            if (settings.enablePhoto) ...<Widget>[
              const SizedBox(height: 16),
              if (_photoBytes != null)
                ClipRRect(borderRadius: BorderRadius.circular(18), child: Image.memory(_photoBytes!, height: 180, fit: BoxFit.cover)),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _submitting ? null : _capturePhoto,
                icon: const Icon(Icons.camera_alt_rounded),
                label: Text(_photoBytes == null ? 'Take proof photo${_photoRequired ? ' *' : ''}' : 'Retake photo'),
              ),
            ],
            if (settings.enableRecipientName) ...<Widget>[
              const SizedBox(height: 12),
              TextField(controller: _recipient, decoration: InputDecoration(labelText: 'Recipient name${settings.requireRecipientName ? ' *' : ''}')),
            ],
            if (settings.enablePin || settings.enableBarcode) ...<Widget>[
              const SizedBox(height: 12),
              Row(children: <Widget>[
                if (settings.enablePin)
                  Expanded(child: TextField(controller: _pin, decoration: InputDecoration(labelText: 'PIN${settings.requirePin ? ' *' : ''}'))),
                if (settings.enablePin && settings.enableBarcode) const SizedBox(width: 10),
                if (settings.enableBarcode)
                  Expanded(child: TextField(controller: _barcode, decoration: InputDecoration(labelText: 'Barcode / ref${settings.requireBarcode ? ' *' : ''}'))),
              ]),
            ],
            const SizedBox(height: 12),
            TextField(controller: _packageCount, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Packages handed over')),
            if (settings.enableSignature) ...<Widget>[
              const SizedBox(height: 16),
              Row(children: <Widget>[
                Expanded(child: Text('Signature${settings.requireSignature ? ' *' : ''}', style: const TextStyle(fontWeight: FontWeight.w900))),
                TextButton(onPressed: () => setState(_signaturePoints.clear), child: const Text('Clear')),
              ]),
              RepaintBoundary(
                key: _signatureKey,
                child: GestureDetector(
                  onPanStart: (details) => setState(() => _signaturePoints.add(details.localPosition)),
                  onPanUpdate: (details) => setState(() => _signaturePoints.add(details.localPosition)),
                  onPanEnd: (_) => setState(() => _signaturePoints.add(null)),
                  child: Container(
                    height: 150,
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFD5D8DD))),
                    child: CustomPaint(painter: _SignaturePainter(_signaturePoints), size: Size.infinite),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 12),
            TextField(controller: _note, minLines: 2, maxLines: 3, decoration: const InputDecoration(labelText: 'Driver note')),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.verified_rounded),
              label: const Text('Save proof & complete stop'),
            ),
          ],
        ),
      ),
    );
  }
}

class _SignaturePainter extends CustomPainter {
  const _SignaturePainter(this.points);
  final List<Offset?> points;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = Colors.white);
    final paint = Paint()
      ..color = const Color(0xFF111111)
      ..strokeWidth = 2.4
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < points.length - 1; i++) {
      final a = points[i];
      final b = points[i + 1];
      if (a != null && b != null) canvas.drawLine(a, b, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _SignaturePainter oldDelegate) => true;
}

class _StopListTile extends StatelessWidget {
  const _StopListTile({required this.stop, required this.selected, required this.color});
  final OperationStop stop;
  final bool selected;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFFEAF2FF) : Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: selected ? const Color(0xFF8BB6FF) : const Color(0xFFE5E7EB)),
        ),
        child: Row(children: <Widget>[
          CircleAvatar(backgroundColor: color, foregroundColor: Colors.white, child: Text('${stop.sequence}', style: const TextStyle(fontWeight: FontWeight.w900))),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text('${stop.operationLabel} · ${stop.status.replaceAll('_', ' ')}', style: const TextStyle(fontWeight: FontWeight.w900)),
            const SizedBox(height: 3),
            Text(stop.address.isEmpty ? stop.name : stop.address, maxLines: 2, overflow: TextOverflow.ellipsis),
          ])),
          if (stop.isCompleted) const Icon(Icons.check_circle_rounded, color: Color(0xFF0B8F55)),
        ]),
      );
}

class _AllStopsDoneCard extends StatelessWidget {
  const _AllStopsDoneCard();
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(color: const Color(0xFFEAF8F1), borderRadius: BorderRadius.circular(22)),
        child: const Column(children: <Widget>[
          Icon(Icons.task_alt_rounded, size: 42, color: Color(0xFF0B8F55)),
          SizedBox(height: 10),
          Text('All route stops are closed', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          SizedBox(height: 4),
          Text('The platform is finalising this operations job.', textAlign: TextAlign.center),
        ]),
      );
}

class _NumberedStopMarker extends StatelessWidget {
  const _NumberedStopMarker({required this.number, required this.color, required this.selected});
  final int number;
  final Color color;
  final bool selected;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: selected ? 4 : 2),
          boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x33000000), blurRadius: 8)],
        ),
        child: Center(child: Text('$number', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
      );
}

class _DriverMarker extends StatelessWidget {
  const _DriverMarker();
  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(color: const Color(0xFF111111), shape: BoxShape.circle, border: Border.all(color: Colors.white, width: 4)),
        child: const Icon(Icons.navigation_rounded, color: Colors.white),
      );
}

class _Chip extends StatelessWidget {
  const _Chip({required this.text});
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(99), border: Border.all(color: const Color(0xFFE2E5E9))),
        child: Text(text, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
      );
}
