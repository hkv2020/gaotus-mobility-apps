from pathlib import Path

root=Path('passenger')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.6+17','version: 0.5.7+18','version')
replace_one('lib/config/app_config.dart',"static const version = '0.5.6';","static const version = '0.5.7';",'app version')

p=root/'pubspec.yaml'
s=p.read_text()
if 'audioplayers:' not in s:
    s=s.replace('  flutter_local_notifications: ^19.5.0\n','  flutter_local_notifications: ^19.5.0\n  audioplayers: ^6.5.0\n',1)
p.write_text(s)

# Direct foreground playback so sound does not depend only on Android notification channel state.
p=root/'lib/services/passenger_notification_service.dart'
s=p.read_text()
if "package:audioplayers/audioplayers.dart" not in s:
    s=s.replace("import 'package:flutter_local_notifications/flutter_local_notifications.dart';\n","import 'package:flutter_local_notifications/flutter_local_notifications.dart';\nimport 'package:audioplayers/audioplayers.dart';\n",1)
if 'final AudioPlayer _audio = AudioPlayer();' not in s:
    s=s.replace('  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();\n','  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();\n  final AudioPlayer _audio = AudioPlayer();\n',1)
if 'Future<void> _playAlert()' not in s:
    marker='  Future<void> showRideUpdate({\n'
    method="""  Future<void> _playAlert() async {
    try {
      await _audio.stop();
      await _audio.play(AssetSource('audio/gaotus_alert.mp3'), volume: 1.0);
    } catch (_) {}
  }

"""
    if marker not in s: raise SystemExit('notification method marker missing')
    s=s.replace(marker,method+marker,1)
s=s.replace("    if (!_ready || !Platform.isAndroid) return;\n    const android = AndroidNotificationDetails(\n      'gmp_passenger_updates_v2',","    await _playAlert();\n    if (!_ready || !Platform.isAndroid) return;\n    const android = AndroidNotificationDetails(\n      'gmp_passenger_updates_v3',",1)
s=s.replace("    if (!_ready || !Platform.isAndroid) return;\n    const android = AndroidNotificationDetails(\n      'gmp_passenger_messages_v2',","    await _playAlert();\n    if (!_ready || !Platform.isAndroid) return;\n    const android = AndroidNotificationDetails(\n      'gmp_passenger_messages_v3',",1)
p.write_text(s)

# Atomic passenger live snapshot.
p=root/'lib/core/api_client.dart'
s=p.read_text()
marker="  Future<Map<String,dynamic>> driverLocation(int id) => request('POST','/customer/booking/$id/driver-location');\n"
if 'liveSnapshot(int id)' not in s:
    if marker not in s: raise SystemExit('api driver location marker missing')
    s=s.replace(marker,marker+"  Future<Map<String,dynamic>> liveSnapshot(int id) => request('POST','/customer/booking/$id/live-snapshot');\n",1)
p.write_text(s)

p=root/'lib/state/passenger_session.dart'
s=p.read_text()
if 'DateTime? _nearbyLastNonEmptyAt;' not in s:
    s=s.replace('  bool _bookingRefreshInFlight=false;\n','  bool _bookingRefreshInFlight=false;\n  DateTime? _nearbyLastNonEmptyAt;\n',1)

# Replace booking refresh request with atomic snapshot; tracking follows the same authoritative response.
old="""      final r=await _api!.booking(id).timeout(const Duration(seconds:5));
      final b=PassengerBooking.fromJson(Map<String,dynamic>.from(r['booking'] as Map));
"""
new="""      final r=await _api!.liveSnapshot(id).timeout(const Duration(seconds:5));
      final b=PassengerBooking.fromJson(Map<String,dynamic>.from(r['booking'] as Map));
      final rawTracking=r['tracking'];
      if(rawTracking is Map){
        tracking=DriverTracking.fromJson(Map<String,dynamic>.from(rawTracking)).keepLastLocation(tracking);
      }
"""
if old not in s: raise SystemExit('booking live snapshot request marker missing')
s=s.replace(old,new,1)

# Nearby cars: wider radius and sticky last-known cars through transient transport gaps.
s=s.replace('Future<void> refreshNearby(double lat,double lng,{double radiusKm=8,int limit=12}) async {','Future<void> refreshNearby(double lat,double lng,{double radiusKm=12,int limit=20}) async {',1)
old="""      nearbyCars=merged.take(limit).toList();
      notifyListeners();
"""
new="""      final next=merged.take(limit).toList();
      final now=DateTime.now();
      if(next.isNotEmpty){
        nearbyCars=next;
        _nearbyLastNonEmptyAt=now;
      }else{
        final last=_nearbyLastNonEmptyAt;
        if(last==null||now.difference(last)>const Duration(seconds:45)){
          nearbyCars=<NearbyCar>[];
        }
      }
      notifyListeners();
"""
if old not in s: raise SystemExit('nearby assignment marker missing')
s=s.replace(old,new,1)
p.write_text(s)

# Refresh nearby slightly faster and keep the 3D cars compact.
p=root/'lib/screens/home_screen.dart'
s=p.read_text()
s=s.replace('nearbyTimer=Timer.periodic(const Duration(seconds:4),(_)=>unawaited(_refreshNearby()));','nearbyTimer=Timer.periodic(const Duration(seconds:3),(_)=>unawaited(_refreshNearby()));',1)
s=s.replace('await widget.session.refreshNearby(lat,lng);','await widget.session.refreshNearby(lat,lng,radiusKm:12,limit:20);',1)
s=s.replace('unawaited(widget.session.refreshNearby(p.latitude,p.longitude));','unawaited(widget.session.refreshNearby(p.latitude,p.longitude,radiusKm:12,limit:20));',1)
s=s.replace('unawaited(widget.session.refreshNearby(selected.lat,selected.lng));','unawaited(widget.session.refreshNearby(selected.lat,selected.lng,radiusKm:12,limit:20));',1)
s=s.replace('Passenger v0.5.6','Passenger v0.5.7')
p.write_text(s)

# Trip critical poll now gets booking + tracking in one authoritative request; the separate
# tracking refresh remains only as a realtime accelerator.
p=root/'lib/screens/trip_screen.dart'
s=p.read_text()
s=s.replace("""    criticalPoll=Timer.periodic(const Duration(seconds:2),(_){
      unawaited(widget.session.refreshBooking(widget.bookingId,silent:true));
      unawaited(widget.session.refreshTracking(widget.bookingId));
    });
""","""    criticalPoll=Timer.periodic(const Duration(seconds:2),(_){
      unawaited(widget.session.refreshBooking(widget.bookingId,silent:true));
    });
""",1)
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.7+18','audioplayers:'],
  'lib/config/app_config.dart':["version = '0.5.7'"],
  'lib/core/api_client.dart':['liveSnapshot(int id)'],
  'lib/services/passenger_notification_service.dart':['AssetSource','gmp_passenger_updates_v3','gmp_passenger_messages_v3'],
  'lib/state/passenger_session.dart':['_nearbyLastNonEmptyAt','liveSnapshot(id)','Duration(seconds:45)','radiusKm=12'],
  'lib/screens/home_screen.dart':['Passenger v0.5.7','Duration(seconds:3)','radiusKm:12'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
print('Passenger v0.5.7 nearby + atomic ride sync + direct sound patch applied')
