import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

final class OfferNotificationService {
  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  final AudioPlayer _player = AudioPlayer();
  bool initialized = false;
  static const String channelId = 'gmp_trip_requests_v3';

  Future<void> initialize() async {
    try {
      const android = AndroidInitializationSettings('@mipmap/ic_launcher');
      const ios = DarwinInitializationSettings();
      await _plugin.initialize(const InitializationSettings(android: android, iOS: ios));
      if (Platform.isAndroid) {
        final androidPlugin = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
        await androidPlugin?.requestNotificationsPermission();
        const channel = AndroidNotificationChannel(
          channelId,
          'Trip requests',
          description: 'Nearby passenger trip requests',
          importance: Importance.max,
          playSound: true,
          sound: RawResourceAndroidNotificationSound('gaotus_alert'),
          enableVibration: true,
        );
        await androidPlugin?.createNotificationChannel(channel);
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
      await _player.play(AssetSource('audio/gaotus_alert.mp3'), volume: 1.0);
    } catch (_) {}
  }

  Future<void> showOffer({required int id, required String pickup, required String dropoff, required double total}) async {
    await _playForegroundSound();
    if (!initialized) return;
    const android = AndroidNotificationDetails(
      channelId,
      'Trip requests',
      channelDescription: 'Nearby passenger trip requests',
      importance: Importance.max,
      priority: Priority.max,
      playSound: false,
      enableVibration: true,
      visibility: NotificationVisibility.public,
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

  Future<void> dispose() async {
    try { await _player.dispose(); } catch (_) {}
  }
}
