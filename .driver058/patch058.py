from pathlib import Path
import math
import struct
import wave

root = Path('driver')

def replace_one(path, old, new, label):
    p = root / path
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old, new, 1))

replace_one('pubspec.yaml', 'version: 0.5.7+12', 'version: 0.5.8+13', 'version')
replace_one('lib/config/app_config.dart', "static const String version = '0.5.7';", "static const String version = '0.5.8';", 'app version')

asset = root / 'assets/audio/gaotus_alert_long.wav'
asset.parent.mkdir(parents=True, exist_ok=True)
rate = 44100
pattern = [
    (0.34, 880.0), (0.09, 0.0), (0.34, 1175.0), (0.16, 0.0),
    (0.34, 880.0), (0.09, 0.0), (0.34, 1320.0), (0.22, 0.0),
] * 3
frames = []
phase = 0.0
for duration, freq in pattern:
    samples = max(1, int(rate * duration))
    for i in range(samples):
        if freq <= 0:
            sample = 0.0
        else:
            attack = min(1.0, i / max(1, int(rate * 0.012)))
            release = min(1.0, (samples - i - 1) / max(1, int(rate * 0.025)))
            env = max(0.0, min(attack, release))
            sample = 0.78 * math.sin(phase) + 0.16 * math.sin(phase * 1.5)
            sample *= env * 0.96
            phase += 2.0 * math.pi * freq / rate
        frames.append(max(-32767, min(32767, int(sample * 32767))))
with wave.open(str(asset), 'wb') as out:
    out.setnchannels(1)
    out.setsampwidth(2)
    out.setframerate(rate)
    out.writeframes(b''.join(struct.pack('<h', value) for value in frames))

p = root / 'pubspec.yaml'
s = p.read_text()
if 'assets/audio/gaotus_alert_long.wav' not in s:
    if '    - assets/audio/gaotus_alert.mp3\n' in s:
        s = s.replace('    - assets/audio/gaotus_alert.mp3\n', '    - assets/audio/gaotus_alert.mp3\n    - assets/audio/gaotus_alert_long.wav\n', 1)
    else:
        s = s.replace('flutter:\n  uses-material-design: true\n', 'flutter:\n  uses-material-design: true\n  assets:\n    - assets/audio/gaotus_alert_long.wav\n', 1)
p.write_text(s)

p = root / 'tool/bootstrap_platforms.sh'
s = p.read_text()
copy_line = 'mkdir -p android/app/src/main/res/raw\ncp assets/audio/gaotus_alert_long.wav android/app/src/main/res/raw/gaotus_alert_long.wav\n'
if 'android/app/src/main/res/raw/gaotus_alert_long.wav' not in s:
    marker = 'cp assets/audio/gaotus_alert.mp3 android/app/src/main/res/raw/gaotus_alert.mp3\n'
    if marker in s:
        s = s.replace(marker, marker + copy_line, 1)
    else:
        s = s.replace('python3 tool/patch_platforms.py\n', 'python3 tool/patch_platforms.py\n' + copy_line, 1)
p.write_text(s)

(root / 'lib/services/location_service.dart').write_text(r'''import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:geolocator_android/geolocator_android.dart';
import 'package:geolocator_apple/geolocator_apple.dart';

final class LocationService {
  StreamSubscription<Position>? _subscription;

  bool get running => _subscription != null;

  Future<LocationPermission> ensurePermission() async {
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled) {
      throw StateError('Location services are disabled. Enable GPS and try again.');
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) permission = await Geolocator.requestPermission();
    if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
      throw StateError('Location permission is required for driver mode.');
    }
    return permission;
  }

  LocationSettings _settings() {
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return AndroidSettings(
        accuracy: LocationAccuracy.bestForNavigation,
        distanceFilter: 3,
        intervalDuration: const Duration(seconds: 3),
        foregroundNotificationConfig: const ForegroundNotificationConfig(
          notificationTitle: 'Gaotus Mobility Driver is online',
          notificationText: 'Location sharing is active for dispatch and live tracking.',
          enableWakeLock: true,
        ),
      );
    }
    if (!kIsWeb && (defaultTargetPlatform == TargetPlatform.iOS || defaultTargetPlatform == TargetPlatform.macOS)) {
      return AppleSettings(
        accuracy: LocationAccuracy.bestForNavigation,
        activityType: ActivityType.automotiveNavigation,
        distanceFilter: 3,
        pauseLocationUpdatesAutomatically: false,
        showBackgroundLocationIndicator: true,
      );
    }
    return const LocationSettings(accuracy: LocationAccuracy.bestForNavigation, distanceFilter: 3);
  }

  Future<Position> current() async {
    await ensurePermission();
    return Geolocator.getCurrentPosition(locationSettings: _settings()).timeout(const Duration(seconds: 8));
  }

  Future<Position?> lastKnown() async {
    try {
      await ensurePermission();
      return await Geolocator.getLastKnownPosition();
    } catch (_) {
      return null;
    }
  }

  Future<void> start({
    required void Function(Position position) onPosition,
    void Function(Object error)? onError,
  }) async {
    if (_subscription != null) return;
    await ensurePermission();
    _subscription = Geolocator.getPositionStream(locationSettings: _settings()).listen(
      onPosition,
      onError: onError,
      cancelOnError: false,
    );
    // Prime without blocking the continuous stream. Cached GPS makes map startup
    // immediate, while the fresh fix replaces it as soon as Android supplies one.
    unawaited(_prime(onPosition));
  }

  Future<void> _prime(void Function(Position position) onPosition) async {
    try {
      final cached = await Geolocator.getLastKnownPosition();
      if (cached != null) onPosition(cached);
    } catch (_) {}
    try {
      final fresh = await Geolocator.getCurrentPosition(locationSettings: _settings()).timeout(const Duration(seconds: 8));
      onPosition(fresh);
    } catch (_) {}
  }

  Future<void> restart({
    required void Function(Position position) onPosition,
    void Function(Object error)? onError,
  }) async {
    await stop();
    await start(onPosition: onPosition, onError: onError);
  }

  Future<void> stop() async {
    await _subscription?.cancel();
    _subscription = null;
  }

  Future<void> dispose() => stop();
}
''')

(root / 'lib/services/offer_notification_service.dart').write_text(r'''import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

final class OfferNotificationService {
  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  final AudioPlayer _player = AudioPlayer();
  bool initialized = false;

  static const String tripChannelId = 'gmp_trip_requests_v4';
  static const String chatChannelId = 'gmp_driver_messages_v4';

  Future<void> initialize() async {
    try {
      const android = AndroidInitializationSettings('@mipmap/ic_launcher');
      const ios = DarwinInitializationSettings();
      await _plugin.initialize(const InitializationSettings(android: android, iOS: ios));
      if (Platform.isAndroid) {
        final impl = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
        await impl?.requestNotificationsPermission();
        const trip = AndroidNotificationChannel(
          tripChannelId,
          'Trip requests',
          description: 'Nearby passenger trip requests',
          importance: Importance.max,
          playSound: true,
          sound: RawResourceAndroidNotificationSound('gaotus_alert_long'),
          enableVibration: true,
        );
        const chat = AndroidNotificationChannel(
          chatChannelId,
          'Driver messages',
          description: 'Passenger and dispatch chat messages',
          importance: Importance.max,
          playSound: true,
          sound: RawResourceAndroidNotificationSound('gaotus_alert_long'),
          enableVibration: true,
        );
        await impl?.createNotificationChannel(trip);
        await impl?.createNotificationChannel(chat);
      }
      initialized = true;
    } catch (_) {
      initialized = false;
    }
  }

  Future<void> _playForegroundSound() async {
    try {
      await _player.stop();
      await _player.setReleaseMode(ReleaseMode.stop);
      await _player.play(AssetSource('audio/gaotus_alert_long.wav'), volume: 1.0);
    } catch (_) {}
  }

  Future<void> showOffer({required int id, required String pickup, required String dropoff, required double total}) async {
    await _playForegroundSound();
    if (!initialized) return;
    const android = AndroidNotificationDetails(
      tripChannelId,
      'Trip requests',
      channelDescription: 'Nearby passenger trip requests',
      importance: Importance.max,
      priority: Priority.max,
      playSound: false,
      enableVibration: true,
      visibility: NotificationVisibility.public,
      category: AndroidNotificationCategory.call,
      fullScreenIntent: false,
    );
    const ios = DarwinNotificationDetails(presentAlert: true, presentBadge: true, presentSound: true);
    final price = total > 0 ? ' · £${total.toStringAsFixed(2)}' : '';
    final body = pickup.isNotEmpty ? '$pickup${dropoff.isNotEmpty ? ' → $dropoff' : ''}$price' : 'A passenger near you requested a ride$price';
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

  Future<void> showChatMessage({required int eventId, required int bookingId, required String preview}) async {
    await _playForegroundSound();
    if (!initialized) return;
    const android = AndroidNotificationDetails(
      chatChannelId,
      'Driver messages',
      channelDescription: 'Passenger and dispatch chat messages',
      importance: Importance.max,
      priority: Priority.max,
      playSound: false,
      enableVibration: true,
      visibility: NotificationVisibility.public,
      category: AndroidNotificationCategory.message,
    );
    const ios = DarwinNotificationDetails(presentAlert: true, presentBadge: true, presentSound: true);
    try {
      await _plugin.show(
        200000 + ((eventId > 0 ? eventId : bookingId) % 799999),
        'New passenger message',
        preview.trim().isEmpty ? 'Open the ride chat to read the message.' : preview.trim(),
        const NotificationDetails(android: android, iOS: ios),
        payload: 'chat:$bookingId',
      );
    } catch (_) {}
  }

  Future<void> dispose() async {
    try { await _player.dispose(); } catch (_) {}
  }
}
''')

(root / 'lib/screens/nearby_jobs_screen.dart').write_text(r'''import 'dart:async';

import 'package:flutter/material.dart';

import '../models/job_offer.dart';
import '../state/app_session.dart';
import '../widgets/offer_card.dart';
import 'job_screen.dart';

class NearbyJobsScreen extends StatefulWidget {
  const NearbyJobsScreen({super.key, required this.session});
  final AppSession session;

  @override
  State<NearbyJobsScreen> createState() => _NearbyJobsScreenState();
}

class _NearbyJobsScreenState extends State<NearbyJobsScreen> {
  Timer? _refresh;

  @override
  void initState() {
    super.initState();
    _refresh = Timer.periodic(const Duration(seconds: 2), (_) => unawaited(widget.session.refreshOperationalState(silent: true)));
    WidgetsBinding.instance.addPostFrameCallback((_) => unawaited(widget.session.refreshOperationalState(silent: true)));
  }

  @override
  void dispose() {
    _refresh?.cancel();
    super.dispose();
  }

  Future<void> _accept(JobOffer offer) async {
    try {
      await widget.session.acceptOffer(offer);
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => JobScreen(session: widget.session)));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(widget.session.errorMessage ?? 'Could not accept trip.')));
    }
  }

  Future<void> _decline(JobOffer offer) async {
    try {
      await widget.session.declineOffer(offer);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(widget.session.errorMessage ?? 'Could not decline trip.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.session,
      builder: (context, _) {
        final active = widget.session.offers.where((item) => !item.expired).toList();
        final current = widget.session.currentJob;
        return Scaffold(
          appBar: AppBar(
            automaticallyImplyLeading: false,
            title: const Text('Jobs', style: TextStyle(fontWeight: FontWeight.w900)),
            actions: <Widget>[
              IconButton(
                tooltip: 'Refresh jobs',
                onPressed: () => widget.session.refreshOperationalState(),
                icon: const Icon(Icons.refresh_rounded),
              ),
            ],
          ),
          body: RefreshIndicator(
            onRefresh: () => widget.session.refreshOperationalState(),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 110),
              children: <Widget>[
                if (current != null) ...<Widget>[
                  Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(color: const Color(0xFF111111), borderRadius: BorderRadius.circular(24)),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            const CircleAvatar(backgroundColor: Colors.white, child: Icon(Icons.route_rounded, color: Colors.black)),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  const Text('Current job', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 19)),
                                  const SizedBox(height: 2),
                                  Text(current.status.toUpperCase(), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Color(0xFFBFC5CD), fontWeight: FontWeight.w800, fontSize: 12, letterSpacing: .7)),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        _RouteLine(icon: Icons.trip_origin_rounded, text: current.pickup.isEmpty ? 'Pick-up unavailable' : current.pickup),
                        const Padding(
                          padding: EdgeInsets.only(left: 11, top: 2, bottom: 2),
                          child: Align(alignment: Alignment.centerLeft, child: SizedBox(height: 14, child: VerticalDivider(color: Color(0xFF737A84), width: 1, thickness: 1))),
                        ),
                        _RouteLine(icon: Icons.location_on_rounded, text: current.dropoff.isEmpty ? 'Destination unavailable' : current.dropoff),
                        const SizedBox(height: 16),
                        SizedBox(
                          height: 48,
                          child: FilledButton.icon(
                            style: FilledButton.styleFrom(backgroundColor: Colors.white, foregroundColor: Colors.black),
                            onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => JobScreen(session: widget.session))),
                            icon: const Icon(Icons.open_in_new_rounded),
                            label: const Text('Open active job', style: TextStyle(fontWeight: FontWeight.w900)),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 22),
                ],
                Row(
                  children: <Widget>[
                    Expanded(child: Text('Nearby trip requests', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900))),
                    if (active.isNotEmpty) Badge.count(count: active.length),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  current != null
                      ? 'Your active job is shown above. New nearby requests appear here separately.'
                      : 'If you close an offer pop-up, the request stays here until it expires or you respond.',
                  style: const TextStyle(color: Color(0xFF666666), height: 1.35),
                ),
                const SizedBox(height: 16),
                if (active.isEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 38, horizontal: 22),
                    decoration: BoxDecoration(color: const Color(0xFFF4F4F4), borderRadius: BorderRadius.circular(24)),
                    child: Column(
                      children: <Widget>[
                        const Icon(Icons.radar_rounded, size: 40),
                        const SizedBox(height: 12),
                        const Text('No new nearby requests', textAlign: TextAlign.center, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
                        const SizedBox(height: 5),
                        Text(
                          current != null ? 'You still have an active job. New requests will appear here when available.' : 'Stay online. New jobs appear here automatically.',
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: Color(0xFF666666), height: 1.35),
                        ),
                      ],
                    ),
                  )
                else
                  ...active.map((offer) => Padding(
                        padding: const EdgeInsets.only(bottom: 14),
                        child: OfferCard(offer: offer, onAccept: () => _accept(offer), onDecline: () => _decline(offer)),
                      )),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _RouteLine extends StatelessWidget {
  const _RouteLine({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Padding(padding: const EdgeInsets.only(top: 2), child: Icon(icon, size: 22, color: Colors.white)),
          const SizedBox(width: 10),
          Expanded(child: Text(text, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.3, fontWeight: FontWeight.w700))),
        ],
      );
}
''')

p = root / 'lib/state/app_session.dart'
s = p.read_text()
if 'Timer? _gpsWatchdogTimer;' not in s:
    s = s.replace('  Timer? _wordpressHeartbeatTimer;\n', '  Timer? _wordpressHeartbeatTimer;\n  Timer? _gpsWatchdogTimer;\n  DateTime? _lastGpsUpdateAt;\n', 1)
if 'int chatAlertSequence = 0;' not in s:
    s = s.replace('  List<JobOffer> recentOffers = <JobOffer>[];\n', '  List<JobOffer> recentOffers = <JobOffer>[];\n  int chatAlertSequence = 0;\n  int chatAlertBookingId = 0;\n  String chatAlertPreview = \'\';\n  int _lastChatAlertEventId = 0;\n', 1)

old = r'''  Future<void> primeLocation() async {
    try {
      final position = await _location.current();
      _onPosition(position);
      if (isOnline) unawaited(_sendWordPressFallbackPing(position, force: true));
    } catch (error) {
      errorMessage = _message(error);
      notifyListeners();
    }
  }
'''
new = r'''  Future<void> primeLocation() async {
    try {
      final cached = await _location.lastKnown();
      if (cached != null) _onPosition(cached);
    } catch (_) {}
    try {
      final position = await _location.current();
      _onPosition(position);
      if (isOnline) unawaited(_sendWordPressFallbackPing(position, force: true));
    } catch (error) {
      if (_lastPosition == null) errorMessage = _message(error);
      notifyListeners();
    }
  }

  Future<void> recoverLocation({bool forceRestart = false}) async {
    if (!authenticated || !isOnline) return;
    try {
      if (forceRestart) await _location.stop();
      await _startLocation();
      final cached = await _location.lastKnown();
      if (cached != null) _onPosition(cached);
      unawaited(primeLocation());
    } catch (error) {
      gpsRunning = false;
      errorMessage = 'GPS: ${_message(error)}';
      notifyListeners();
    }
  }
'''
if old not in s:
    raise SystemExit('primeLocation marker missing')
s = s.replace(old, new, 1)

old = r'''  void _onPosition(Position position) {
    _lastPosition = position;
    _pendingPosition = position;
    notifyListeners();
    unawaited(_flushLatestLocation());
    final now = DateTime.now();
    if (_lastWordPressFallbackPing == null || now.difference(_lastWordPressFallbackPing!) >= const Duration(seconds: 5)) {
      unawaited(_sendWordPressFallbackPing(position));
    }
  }
'''
new = r'''  void _onPosition(Position position) {
    final previous = _lastPosition;
    if (previous != null && position.timestamp.isBefore(previous.timestamp)) return;
    _lastPosition = position;
    _lastGpsUpdateAt = DateTime.now();
    _pendingPosition = position;
    gpsRunning = true;
    errorMessage = errorMessage?.startsWith('GPS:') == true ? null : errorMessage;
    notifyListeners();
    unawaited(_flushLatestLocation());
    final now = DateTime.now();
    if (_lastWordPressFallbackPing == null || now.difference(_lastWordPressFallbackPing!) >= const Duration(seconds: 5)) {
      unawaited(_sendWordPressFallbackPing(position));
    }
  }
'''
if old not in s:
    raise SystemExit('onPosition marker missing')
s = s.replace(old, new, 1)

needle = r'''    _wordpressHeartbeatTimer?.cancel();
    _wordpressHeartbeatTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      final position = _lastPosition;
      if (authenticated && isOnline && position != null) unawaited(_sendWordPressFallbackPing(position, force: true));
    });
    if (isOnline) unawaited(primeLocation());
'''
replacement = r'''    _wordpressHeartbeatTimer?.cancel();
    _wordpressHeartbeatTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      final position = _lastPosition;
      if (authenticated && isOnline && position != null) unawaited(_sendWordPressFallbackPing(position, force: true));
    });
    _gpsWatchdogTimer?.cancel();
    _gpsWatchdogTimer = Timer.periodic(const Duration(seconds: 8), (_) {
      if (!authenticated || !isOnline) return;
      final last = _lastGpsUpdateAt;
      final stale = last == null || DateTime.now().difference(last) > const Duration(seconds: 16);
      if (!_location.running || stale) unawaited(recoverLocation(forceRestart: true));
    });
    if (isOnline) unawaited(recoverLocation());
'''
if needle not in s:
    raise SystemExit('runtime gps watchdog marker missing')
s = s.replace(needle, replacement, 1)

marker = '  void _onRealtimeEvent(Map<String, dynamic> event) {\n'
if 'void _announceChatAlert(' not in s:
    helper = r'''  void _announceChatAlert({required int eventId, required int bookingId, required String preview}) {
    if (eventId > 0 && eventId == _lastChatAlertEventId) return;
    if (eventId > 0) _lastChatAlertEventId = eventId;
    chatAlertBookingId = bookingId > 0 ? bookingId : (currentJob?.id ?? 0);
    chatAlertPreview = preview.trim().isEmpty ? 'You have a new passenger message.' : preview.trim();
    chatAlertSequence++;
    HapticFeedback.heavyImpact();
    unawaited(_offerNotifications.showChatMessage(
      eventId: eventId,
      bookingId: chatAlertBookingId,
      preview: chatAlertPreview,
    ));
    notifyListeners();
  }

'''
    if marker not in s:
        raise SystemExit('realtime event marker missing')
    s = s.replace(marker, helper + marker, 1)

old = r'''  void _onRealtimeEvent(Map<String, dynamic> event) {
    final eventId = intValue(event['event_id']);
    if (eventId > _lastRealtimeEventId) _lastRealtimeEventId = eventId;
    final type = event['type']?.toString() ?? '';
    if (type == 'job.offer') {
'''
new = r'''  void _onRealtimeEvent(Map<String, dynamic> event) {
    final eventId = intValue(event['event_id']);
    if (eventId > _lastRealtimeEventId) _lastRealtimeEventId = eventId;
    final type = event['type']?.toString() ?? '';
    if (type == 'chat.message') {
      final payload = mapValue(event['payload']);
      final message = mapValue(payload['message']);
      _announceChatAlert(
        eventId: eventId,
        bookingId: intValue(event['booking_id'] ?? payload['booking_id']),
        preview: (message['message'] ?? payload['message_text'] ?? '').toString(),
      );
      return;
    }
    if (type == 'job.offer') {
'''
if old not in s:
    raise SystemExit('chat realtime insertion marker missing')
s = s.replace(old, new, 1)

old = r'''  void _onPushMessage(Map<String, dynamic> data) {
    final eventType = data['event_type']?.toString() ?? '';
    if (eventType == 'job.offer') HapticFeedback.heavyImpact();
    if (eventType.startsWith('job.') || eventType.startsWith('booking.') || eventType == 'trip.completed') {
      unawaited(refreshOperationalState(silent: true));
    }
  }
'''
new = r'''  void _onPushMessage(Map<String, dynamic> data) {
    final eventType = data['event_type']?.toString() ?? '';
    if (eventType == 'chat.message') {
      _announceChatAlert(
        eventId: intValue(data['event_id']),
        bookingId: intValue(data['booking_id']),
        preview: (data['notification_body'] ?? '').toString(),
      );
      return;
    }
    if (eventType == 'job.offer') HapticFeedback.heavyImpact();
    if (eventType.startsWith('job.') || eventType.startsWith('booking.') || eventType == 'trip.completed') {
      unawaited(refreshOperationalState(silent: true));
    }
  }
'''
if old not in s:
    raise SystemExit('push chat marker missing')
s = s.replace(old, new, 1)

s = s.replace('      _wordpressHeartbeatTimer?.cancel();\n      _wordpressHeartbeatTimer = null;\n', '      _wordpressHeartbeatTimer?.cancel();\n      _wordpressHeartbeatTimer = null;\n      _gpsWatchdogTimer?.cancel();\n      _gpsWatchdogTimer = null;\n', 1)
s = s.replace('      recentOffers=<JobOffer>[];\n      await _store.clearSession();', '      recentOffers=<JobOffer>[];\n      chatAlertSequence = 0;\n      chatAlertBookingId = 0;\n      chatAlertPreview = \'\';\n      _lastChatAlertEventId = 0;\n      _lastGpsUpdateAt = null;\n      await _store.clearSession();', 1)
s = s.replace('    _wordpressHeartbeatTimer?.cancel();\n    _locationRetryTimer?.cancel();', '    _wordpressHeartbeatTimer?.cancel();\n    _gpsWatchdogTimer?.cancel();\n    _locationRetryTimer?.cancel();', 1)
p.write_text(s)

p = root / 'lib/screens/driver_home_screen.dart'
s = p.read_text()
if "import 'chat_screen.dart';" not in s:
    s = s.replace("import 'job_screen.dart';\n", "import 'job_screen.dart';\nimport 'chat_screen.dart';\n", 1)
s = s.replace('class _DriverHomeScreenState extends State<DriverHomeScreen> {', 'class _DriverHomeScreenState extends State<DriverHomeScreen> with WidgetsBindingObserver {', 1)
if 'int _lastChatAlertSequence = 0;' not in s:
    s = s.replace('  bool _presentingOffer = false;\n', '  bool _presentingOffer = false;\n  int _lastChatAlertSequence = 0;\n', 1)
s = s.replace('    widget.session.addListener(_sessionChanged);\n', '    widget.session.addListener(_sessionChanged);\n    WidgetsBinding.instance.addObserver(this);\n', 1)
s = s.replace('    widget.session.removeListener(_sessionChanged);\n    super.dispose();', '    widget.session.removeListener(_sessionChanged);\n    WidgetsBinding.instance.removeObserver(this);\n    super.dispose();', 1)

if 'void didChangeAppLifecycleState' not in s:
    marker = '  void _sessionChanged() {\n'
    lifecycle = r'''  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && widget.session.isOnline) {
      unawaited(widget.session.recoverLocation(forceRestart: true));
    }
  }

  void _showIncomingChatPopup() {
    final sequence = widget.session.chatAlertSequence;
    if (sequence <= _lastChatAlertSequence || !mounted) return;
    _lastChatAlertSequence = sequence;
    final preview = widget.session.chatAlertPreview;
    final bookingId = widget.session.chatAlertBookingId > 0 ? widget.session.chatAlertBookingId : (widget.session.currentJob?.id ?? 0);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final messenger = ScaffoldMessenger.of(context);
      messenger.hideCurrentSnackBar();
      messenger.showSnackBar(
        SnackBar(
          duration: const Duration(seconds: 9),
          behavior: SnackBarBehavior.floating,
          content: Row(
            children: <Widget>[
              const Icon(Icons.chat_bubble_rounded, color: Colors.white),
              const SizedBox(width: 10),
              Expanded(child: Text(preview.isEmpty ? 'New passenger message' : preview, maxLines: 2, overflow: TextOverflow.ellipsis)),
            ],
          ),
          action: bookingId > 0
              ? SnackBarAction(
                  label: 'OPEN',
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => DriverChatScreen(session: widget.session, bookingId: bookingId))),
                )
              : null,
        ),
      );
    });
  }

'''
    if marker not in s:
        raise SystemExit('home sessionChanged marker missing')
    s = s.replace(marker, lifecycle + marker, 1)

s = s.replace('  void _sessionChanged() {\n    if (!mounted || _presentingOffer) return;\n', '  void _sessionChanged() {\n    if (!mounted) return;\n    _showIncomingChatPopup();\n    if (_presentingOffer) return;\n', 1)

s = s.replace('      unawaited(widget.session.primeLocation());\n', '      unawaited(widget.session.recoverLocation());\n', 1)
s = s.replace("child: _CircleButton(icon: Icons.my_location_rounded, onTap: () => _followDriver(force: true)),", "child: _CircleButton(icon: Icons.my_location_rounded, onTap: () async { await widget.session.recoverLocation(forceRestart: true); _followDriver(force: true); }),", 1)
old_badge = r'''            icon: widget.session.offers.isEmpty
                ? const Icon(Icons.work_outline_rounded)
                : Badge.count(count:widget.session.offers.length,child:const Icon(Icons.work_outline_rounded)),
'''
new_badge = r'''            icon: (widget.session.offers.length + (widget.session.currentJob != null ? 1 : 0)) == 0
                ? const Icon(Icons.work_outline_rounded)
                : Badge.count(count: widget.session.offers.length + (widget.session.currentJob != null ? 1 : 0), child: const Icon(Icons.work_outline_rounded)),
'''
if old_badge not in s:
    raise SystemExit('jobs badge marker missing')
s = s.replace(old_badge, new_badge, 1)
p.write_text(s)

checks = {
    'pubspec.yaml': ['version: 0.5.8+13', 'assets/audio/gaotus_alert_long.wav'],
    'lib/config/app_config.dart': ["version = '0.5.8'"],
    'lib/services/location_service.dart': ['unawaited(_prime(onPosition))', 'getLastKnownPosition', 'Future<void> restart'],
    'lib/services/offer_notification_service.dart': ['gmp_trip_requests_v4', 'gmp_driver_messages_v4', 'gaotus_alert_long', 'showChatMessage'],
    'lib/screens/nearby_jobs_screen.dart': ['Current job', 'Nearby trip requests', 'Open active job'],
    'lib/state/app_session.dart': ['recoverLocation({bool forceRestart = false})', '_gpsWatchdogTimer', "type == 'chat.message'", 'chatAlertSequence'],
    'lib/screens/driver_home_screen.dart': ['WidgetsBindingObserver', 'didChangeAppLifecycleState', '_showIncomingChatPopup', 'DriverChatScreen', 'recoverLocation(forceRestart: true)'],
    'tool/bootstrap_platforms.sh': ['gaotus_alert_long.wav'],
}
for path, needles in checks.items():
    text = (root / path).read_text()
    for needle in needles:
        if needle not in text:
            raise SystemExit(f'missing {needle} in {path}')
if asset.stat().st_size < 100000:
    raise SystemExit('long alert asset unexpectedly small')
print(f'Driver v0.5.8 patch applied; long alert bytes={asset.stat().st_size}')