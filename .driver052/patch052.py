from pathlib import Path

root=Path('driver')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.1+6','version: 0.5.2+7','version')
p=root/'pubspec.yaml'; s=p.read_text()
if 'flutter_local_notifications:' not in s:
    s=s.replace('  firebase_messaging: ^16.7.0\n','  firebase_messaging: ^16.7.0\n  flutter_local_notifications: ^19.5.0\n',1)
p.write_text(s)
replace_one('lib/config/app_config.dart',"static const String version = '0.5.1';","static const String version = '0.5.2';",'app version')

(root/'lib/services/offer_notification_service.dart').write_text(r"""import 'package:flutter_local_notifications/flutter_local_notifications.dart';

final class OfferNotificationService {
  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  bool initialized = false;

  Future<void> initialize() async {
    try {
      const android = AndroidInitializationSettings('@mipmap/ic_launcher');
      const ios = DarwinInitializationSettings();
      await _plugin.initialize(const InitializationSettings(android: android, iOS: ios));
      final androidPlugin = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
      await androidPlugin?.requestNotificationsPermission();
      initialized = true;
    } catch (_) {
      initialized = false;
    }
  }

  Future<void> showOffer({required int id, required String pickup, required String dropoff, required double total}) async {
    if (!initialized) return;
    const android = AndroidNotificationDetails(
      'gmp_trip_requests',
      'Trip requests',
      channelDescription: 'Nearby passenger trip requests',
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      enableVibration: true,
      visibility: NotificationVisibility.public,
    );
    const ios = DarwinNotificationDetails(presentAlert: true, presentBadge: true, presentSound: true);
    final price = total > 0 ? ' · £${total.toStringAsFixed(2)}' : '';
    final body = pickup.isNotEmpty
        ? '${pickup}${dropoff.isNotEmpty ? ' → $dropoff' : ''}$price'
        : 'A passenger near you requested a ride$price';
    try {
      await _plugin.show(
        100000 + (id % 899999),
        'New passenger request nearby',
        body,
        const NotificationDetails(android: android, iOS: ios),
        payload: 'offer:$id',
      );
    } catch (_) {}
  }
}
""")

p=root/'lib/services/location_service.dart'; s=p.read_text()
old="""    if (_subscription != null) return;
    await ensurePermission();
    _subscription = Geolocator.getPositionStream(locationSettings: _settings()).listen(
      onPosition,
      onError: onError,
    );
"""
new="""    if (_subscription != null) return;
    await ensurePermission();
    try {
      final first = await Geolocator.getCurrentPosition(locationSettings: _settings()).timeout(const Duration(seconds: 12));
      onPosition(first);
    } catch (_) {
      // The continuous stream remains the source of truth if the first fix times out.
    }
    _subscription = Geolocator.getPositionStream(locationSettings: _settings()).listen(
      onPosition,
      onError: onError,
    );
"""
if old not in s: raise SystemExit('location start marker missing')
p.write_text(s.replace(old,new,1))

p=root/'lib/services/realtime_service.dart'; s=p.read_text()
s=s.replace("_reconnectTimer = Timer(const Duration(seconds: 30), _open);","_reconnectTimer = Timer(const Duration(seconds: 6), _open);",1)
marker="  Future<bool> sendAvailabilityHttp(String availability) async {\n"
if marker not in s: raise SystemExit('realtime marker missing')
method=r"""  Future<Map<String, dynamic>?> pollDriverEvents({int afterId = 0}) async {
    if (_baseUrl == null || _baseUrl!.isEmpty || _token == null || _token!.isEmpty) return null;
    try {
      final response = await _http.post(
        _httpUri('/http/driver/events'),
        headers: const <String,String>{'Accept':'application/json','Content-Type':'application/json'},
        body: jsonEncode(<String,Object?>{'token':_token,'after_id':afterId}),
      ).timeout(const Duration(seconds: 5));
      if (response.statusCode < 200 || response.statusCode >= 300) return null;
      final decoded = jsonDecode(response.body);
      return decoded is Map ? Map<String,dynamic>.from(decoded) : null;
    } catch (_) { return null; }
  }

"""
p.write_text(s.replace(marker,method+marker,1))

p=root/'lib/state/app_session.dart'; s=p.read_text()
s=s.replace("import '../services/location_service.dart';\n","import '../services/location_service.dart';\nimport '../services/offer_notification_service.dart';\n",1)
s=s.replace("  final PushService _push = PushService();\n","  final PushService _push = PushService();\n  final OfferNotificationService _offerNotifications = OfferNotificationService();\n",1)
s=s.replace("  Timer? _fallbackPollTimer;\n  Timer? _reconcileTimer;\n","  Timer? _fallbackPollTimer;\n  Timer? _eventPollTimer;\n  Timer? _reconcileTimer;\n  bool _operationalRefreshInFlight = false;\n  bool _eventPollInFlight = false;\n  int _lastRealtimeEventId = 0;\n  final Set<int> _seenOfferIds = <int>{};\n",1)
s=s.replace("    await _push.initialize();\n    pushAvailable = _push.available;\n","    await _offerNotifications.initialize();\n    await _push.initialize();\n    pushAvailable = _push.available;\n",1)
old_runtime="""    _fallbackPollTimer?.cancel();
    _fallbackPollTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      if (!realtimeConnected) unawaited(refreshOperationalState(silent: true));
    });
    _reconcileTimer?.cancel();
    _reconcileTimer = Timer.periodic(const Duration(minutes: 2), (_) {
      unawaited(refreshAll(silent: true));
    });
"""
new_runtime="""    _fallbackPollTimer?.cancel();
    _fallbackPollTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      unawaited(_pollOperationalSafetyNet());
    });
    _eventPollTimer?.cancel();
    _eventPollTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      unawaited(_pollRealtimeEvents());
    });
    _reconcileTimer?.cancel();
    _reconcileTimer = Timer.periodic(const Duration(seconds: 45), (_) {
      unawaited(refreshAll(silent: true));
    });
"""
if old_runtime not in s: raise SystemExit('runtime timer marker missing')
s=s.replace(old_runtime,new_runtime,1)
marker="  Future<void> _loadAll(ApiClient api) async {\n"
if marker not in s: raise SystemExit('loadAll marker missing')
helpers=r"""  Future<void> _pollOperationalSafetyNet() async {
    if (!authenticated || _operationalRefreshInFlight) return;
    _operationalRefreshInFlight = true;
    try {
      await refreshOperationalState(silent: true).timeout(const Duration(seconds: 8));
    } catch (_) {
      // Realtime and the next safety-net tick remain available.
    } finally {
      _operationalRefreshInFlight = false;
    }
  }

  Future<void> _pollRealtimeEvents() async {
    if (!authenticated || _eventPollInFlight || realtimeUrl == null || token == null) return;
    _eventPollInFlight = true;
    try {
      final data = await _realtime.pollDriverEvents(afterId: _lastRealtimeEventId);
      if (data == null) return;
      final raw = data['events'];
      if (raw is List) {
        for (final item in raw.whereType<Map>()) {
          final event = Map<String, dynamic>.from(item);
          final id = intValue(event['event_id']);
          if (id > _lastRealtimeEventId) _lastRealtimeEventId = id;
          _onRealtimeEvent(event);
        }
      }
      final last = intValue(data['last_id']);
      if (last > _lastRealtimeEventId) _lastRealtimeEventId = last;
    } catch (_) {
      // WordPress operational polling is the final fallback.
    } finally {
      _eventPollInFlight = false;
    }
  }

"""
s=s.replace(marker,helpers+marker,1)
old_apply="""  void _applyOffers(Map<String, dynamic> data) {
    final raw = data['offers'];
    if (raw is! List) {
      offers = <JobOffer>[];
      return;
    }
    offers = raw
        .whereType<Map>()
        .map((item) => JobOffer.fromJson(Map<String, dynamic>.from(item)))
        .where((offer) => !offer.expired && offer.status == 'offered')
        .toList();
  }
"""
new_apply="""  void _applyOffers(Map<String, dynamic> data) {
    final raw = data['offers'];
    if (raw is! List) {
      offers = <JobOffer>[];
      return;
    }
    final next = raw
        .whereType<Map>()
        .map((item) => JobOffer.fromJson(Map<String, dynamic>.from(item)))
        .where((offer) => !offer.expired && offer.status == 'offered')
        .toList();
    offers = next;
    for (final offer in next) {
      if (_seenOfferIds.add(offer.id)) unawaited(_announceOffer(offer));
    }
  }

  Future<void> _announceOffer(JobOffer offer) async {
    HapticFeedback.heavyImpact();
    await _offerNotifications.showOffer(
      id: offer.id,
      pickup: offer.booking.pickup,
      dropoff: offer.booking.dropoff,
      total: offer.booking.total,
    );
  }
"""
if old_apply not in s: raise SystemExit('apply offers marker missing')
s=s.replace(old_apply,new_apply,1)
old_accept="""      await api.acceptOffer(offer.id);
      HapticFeedback.heavyImpact();
      await refreshAll(silent: true);
      await _startLocation();
"""
new_accept="""      final data = await api.acceptOffer(offer.id).timeout(const Duration(seconds: 12));
      final rawBooking = data['booking'];
      if (rawBooking is Map) currentJob = Booking.fromJson(Map<String, dynamic>.from(rawBooking));
      offers = offers.where((item) => item.id != offer.id).toList();
      if (driverState != null) {
        driverState = driverState!.copyWith(availability: 'busy', activeBookingId: currentJob?.id ?? offer.bookingId);
      }
      HapticFeedback.heavyImpact();
      notifyListeners();
      unawaited(refreshOperationalState(silent: true));
      unawaited(_startLocation());
"""
if old_accept not in s: raise SystemExit('accept marker missing')
s=s.replace(old_accept,new_accept,1)
old_event="""  void _onRealtimeEvent(Map<String, dynamic> event) {
    final type = event['type']?.toString() ?? '';
    if (type == 'job.offer') {
      HapticFeedback.heavyImpact();
      unawaited(refreshOperationalState(silent: true));
    } else if (type == 'job.assigned' ||
"""
new_event="""  void _onRealtimeEvent(Map<String, dynamic> event) {
    final eventId = intValue(event['event_id']);
    if (eventId > _lastRealtimeEventId) _lastRealtimeEventId = eventId;
    final type = event['type']?.toString() ?? '';
    if (type == 'job.offer') {
      final payload = mapValue(event['payload']);
      if (payload.isNotEmpty) {
        try {
          final offer = JobOffer.fromJson(payload);
          if (!offer.expired && offer.status == 'offered') {
            final index = offers.indexWhere((item) => item.id == offer.id);
            if (index >= 0) offers[index] = offer; else offers.insert(0, offer);
            if (_seenOfferIds.add(offer.id)) unawaited(_announceOffer(offer));
            notifyListeners();
          }
        } catch (_) {}
      }
      unawaited(refreshOperationalState(silent: true));
    } else if (type == 'job.assigned' ||
"""
if old_event not in s: raise SystemExit('realtime event marker missing')
s=s.replace(old_event,new_event,1)
s=s.replace("      _fallbackPollTimer?.cancel();\n      _fallbackPollTimer = null;\n      _reconcileTimer?.cancel();","      _fallbackPollTimer?.cancel();\n      _fallbackPollTimer = null;\n      _eventPollTimer?.cancel();\n      _eventPollTimer = null;\n      _reconcileTimer?.cancel();",1)
s=s.replace("      _pendingPosition = null;\n      await _store.clearSession();","      _pendingPosition = null;\n      _lastRealtimeEventId = 0;\n      _seenOfferIds.clear();\n      await _store.clearSession();",1)
s=s.replace("    _fallbackPollTimer?.cancel();\n    _reconcileTimer?.cancel();","    _fallbackPollTimer?.cancel();\n    _eventPollTimer?.cancel();\n    _reconcileTimer?.cancel();",1)
p.write_text(s)

p=root/'lib/screens/driver_home_screen.dart'; s=p.read_text()
s=s.replace("        isDismissible: false,\n        enableDrag: false,","        isDismissible: true,\n        enableDrag: true,",1)
s=s.replace("        builder: (modalContext) => _OfferSheet(\n          offer: offer,","        builder: (modalContext) => _OfferSheet(\n          session: widget.session,\n          offer: offer,",1)

start=s.index('class _DriverMapHome extends StatelessWidget {')
end=s.index('class _OnlinePanel extends StatelessWidget {')
if start<0 or end<0: raise SystemExit('driver map class markers missing')
new_map=r"""class _DriverMapHome extends StatefulWidget {
  const _DriverMapHome({required this.session, required this.openEarnings, required this.openJob});
  final AppSession session;
  final VoidCallback openEarnings;
  final VoidCallback openJob;

  @override
  State<_DriverMapHome> createState() => _DriverMapHomeState();
}

class _DriverMapHomeState extends State<_DriverMapHome> {
  final MapController _map = MapController();
  LatLng? _lastCameraPosition;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _followDriver(force: true));
  }

  @override
  void didUpdateWidget(covariant _DriverMapHome oldWidget) {
    super.didUpdateWidget(oldWidget);
    WidgetsBinding.instance.addPostFrameCallback((_) => _followDriver());
  }

  void _followDriver({bool force = false}) {
    if (!mounted) return;
    final position = _currentCenter(widget.session);
    final previous = _lastCameraPosition;
    final hasRealGps = widget.session.lastPosition != null ||
        (widget.session.driverState?.latitude != null && widget.session.driverState?.longitude != null);
    if (!hasRealGps && !force) return;
    if (!force && previous != null) {
      final delta = (previous.latitude - position.latitude).abs() + (previous.longitude - position.longitude).abs();
      if (delta < 0.00015) return;
    }
    _lastCameraPosition = position;
    try { _map.move(position, 15.2); } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final session = widget.session;
    final center = _currentCenter(session);
    final online = session.isOnline;
    final currentJob = session.currentJob;
    final today = session.todayEarnings;
    final currency = today?.currency ?? 'GBP';
    final earnings = today?.driverCut ?? 0;
    final hasGps = session.lastPosition != null;
    final markers = <Marker>[
      Marker(
        point: center,
        width: 58,
        height: 58,
        child: Container(
          decoration: BoxDecoration(
            color: online ? const Color(0xFF276EF1) : Colors.white,
            shape: BoxShape.circle,
            border: Border.all(color: online ? Colors.white : Colors.black, width: 4),
            boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x33000000), blurRadius: 14)],
          ),
          child: Icon(Icons.navigation_rounded, color: online ? Colors.white : Colors.black, size: 27),
        ),
      ),
      if (currentJob?.pickupLat != null && currentJob?.pickupLng != null)
        Marker(point: LatLng(currentJob!.pickupLat!, currentJob.pickupLng!), width: 46, height: 46, child: const _JobMapPin(icon: Icons.person_pin_circle_rounded)),
      if (currentJob?.dropoffLat != null && currentJob?.dropoffLng != null)
        Marker(point: LatLng(currentJob!.dropoffLat!, currentJob.dropoffLng!), width: 46, height: 46, child: const _JobMapPin(icon: Icons.flag_rounded)),
    ];

    return Scaffold(
      body: Stack(
        children: <Widget>[
          Positioned.fill(
            child: FlutterMap(
              mapController: _map,
              options: MapOptions(initialCenter: center, initialZoom: online ? 13.5 : 12.5),
              children: <Widget>[
                TileLayer(urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', userAgentPackageName: 'ai.gaotus.gaotus_mobility_driver'),
                MarkerLayer(markers: markers),
              ],
            ),
          ),
          Positioned(top: MediaQuery.paddingOf(context).top + 14, left: 20, child: _CircleButton(icon: Icons.home_rounded, onTap: () {})),
          Positioned(
            top: MediaQuery.paddingOf(context).top + 14,
            right: 20,
            child: _CircleButton(icon: Icons.my_location_rounded, onTap: () => _followDriver(force: true)),
          ),
          Positioned(
            top: MediaQuery.paddingOf(context).top + 82,
            right: 20,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(99), boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x22000000), blurRadius: 8)]),
              child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Icon(hasGps ? Icons.gps_fixed_rounded : Icons.gps_not_fixed_rounded, size: 16, color: hasGps ? const Color(0xFF0B8F55) : const Color(0xFF666666)),
                const SizedBox(width: 5),
                Text(hasGps ? 'GPS live' : 'Finding GPS…', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
              ]),
            ),
          ),
          Positioned(
            top: MediaQuery.paddingOf(context).top + 14,
            left: 110,
            right: 110,
            child: GestureDetector(
              onTap: widget.openEarnings,
              child: Container(
                height: 58,
                decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(30), boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x33000000), blurRadius: 14)]),
                child: Center(child: Text(_money(earnings, currency), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900))),
              ),
            ),
          ),
          Align(alignment: Alignment.bottomCenter, child: _OnlinePanel(session: session, currentJob: currentJob, openJob: widget.openJob)),
        ],
      ),
    );
  }

  static LatLng _currentCenter(AppSession session) {
    final p = session.lastPosition;
    if (p != null) return LatLng(p.latitude, p.longitude);
    final state = session.driverState;
    if (state?.latitude != null && state?.longitude != null) return LatLng(state!.latitude!, state.longitude!);
    final job = session.currentJob;
    if (job?.pickupLat != null && job?.pickupLng != null) return LatLng(job!.pickupLat!, job.pickupLng!);
    return const LatLng(51.5074, -0.1278);
  }

  static String _money(double value, String currency) {
    final symbol = switch (currency.toUpperCase()) {
      'GBP' => '£',
      'EUR' => '€',
      'USD' => r'$',
      'RON' => 'RON ',
      _ => '${currency.toUpperCase()} ',
    };
    return '$symbol${value.toStringAsFixed(2)}';
  }
}

"""
s=s[:start]+new_map+s[end:]

start=s.index('class _OfferSheet extends StatelessWidget {')
end=s.index('class _CircleButton extends StatelessWidget {')
if start<0 or end<0: raise SystemExit('offer sheet markers missing')
new_sheet=r"""class _OfferSheet extends StatefulWidget {
  const _OfferSheet({required this.session, required this.offer, required this.onAccept, required this.onDecline});
  final AppSession session;
  final JobOffer offer;
  final VoidCallback onAccept;
  final VoidCallback onDecline;

  @override
  State<_OfferSheet> createState() => _OfferSheetState();
}

class _OfferSheetState extends State<_OfferSheet> {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    widget.session.addListener(_checkState);
    _timer = Timer.periodic(const Duration(milliseconds: 500), (_) => _checkState());
  }

  void _checkState() {
    if (!mounted) return;
    final stillOpen = widget.session.offers.any((item) => item.id == widget.offer.id && !item.expired);
    if (widget.offer.expired || !stillOpen || widget.session.currentJob != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && Navigator.of(context).canPop()) Navigator.of(context).pop();
      });
    } else {
      setState(() {});
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    widget.session.removeListener(_checkState);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(30))),
        padding: EdgeInsets.fromLTRB(18, 10, 18, 18 + MediaQuery.paddingOf(context).bottom),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Container(width: 44, height: 5, decoration: BoxDecoration(color: const Color(0xFFD7D7D7), borderRadius: BorderRadius.circular(99))),
            const SizedBox(height: 16),
            const Text('New trip request', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900)),
            const SizedBox(height: 12),
            OfferCard(offer: widget.offer, onAccept: widget.onAccept, onDecline: widget.onDecline),
          ],
        ),
      );
}

"""
s=s[:start]+new_sheet+s[end:]
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.2+7','flutter_local_notifications'],
  'lib/state/app_session.dart':['pollDriverEvents','_pollOperationalSafetyNet','_announceOffer','Duration(seconds: 3)'],
  'lib/screens/driver_home_screen.dart':['GPS live','_OfferSheetState','isDismissible: true'],
  'lib/services/realtime_service.dart':['Duration(seconds: 6)','pollDriverEvents'],
  'lib/services/offer_notification_service.dart':['New passenger request nearby'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')

print('Driver v0.5.2 live dispatch patch applied')
