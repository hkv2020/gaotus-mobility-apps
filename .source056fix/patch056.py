from pathlib import Path
import base64

root=Path('passenger')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.5+16','version: 0.5.6+17','version')
replace_one('lib/config/app_config.dart',"static const version = '0.5.5';","static const version = '0.5.6';",'app version')

p=root/'pubspec.yaml'
s=p.read_text()
if 'flutter_local_notifications:' not in s:
    s=s.replace('  firebase_messaging: ^15.1.6\n','  firebase_messaging: ^15.1.6\n  flutter_local_notifications: ^19.5.0\n',1)
if 'assets/audio/gaotus_alert.mp3' not in s:
    s=s.replace('flutter:\n  uses-material-design: true\n','flutter:\n  uses-material-design: true\n  assets:\n    - assets/audio/gaotus_alert.mp3\n',1)
p.write_text(s)

asset=root/'assets/audio/gaotus_alert.mp3'
asset.parent.mkdir(parents=True,exist_ok=True)
asset.write_bytes(base64.b64decode(Path('.source056fix/gaotus_alert.b64').read_text().strip()))

p=root/'tool/bootstrap_platforms.sh'
s=p.read_text()
copy_line='mkdir -p android/app/src/main/res/raw\ncp assets/audio/gaotus_alert.mp3 android/app/src/main/res/raw/gaotus_alert.mp3\n'
if 'android/app/src/main/res/raw/gaotus_alert.mp3' not in s:
    s=s.replace('python3 tool/patch_platforms.py\n', 'python3 tool/patch_platforms.py\n'+copy_line,1)
p.write_text(s)

(root/'lib/services/passenger_notification_service.dart').write_text(r'''import 'dart:io';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';

final class PassengerNotificationService {
  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  bool _ready = false;

  Future<void> initialize() async {
    try {
      const android = AndroidInitializationSettings('@mipmap/ic_launcher');
      const ios = DarwinInitializationSettings();
      await _plugin.initialize(const InitializationSettings(android: android, iOS: ios));
      if (Platform.isAndroid) {
        final impl = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
        await impl?.requestNotificationsPermission();
      }
      _ready = true;
    } catch (_) {
      _ready = false;
    }
  }

  Future<void> showRideUpdate({
    required int bookingId,
    required String title,
    required String body,
  }) async {
    if (!_ready || !Platform.isAndroid) return;
    const android = AndroidNotificationDetails(
      'gmp_passenger_updates_v2',
      'Ride updates',
      channelDescription: 'Driver assignment, ride status and ride messages',
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      sound: RawResourceAndroidNotificationSound('gaotus_alert'),
      enableVibration: true,
      visibility: NotificationVisibility.public,
    );
    try {
      await _plugin.show(
        200000 + (bookingId % 799999),
        title,
        body,
        const NotificationDetails(android: android),
        payload: 'booking:$bookingId',
      );
    } catch (_) {}
  }

  Future<void> showMessage({
    required int bookingId,
    required String title,
    required String body,
  }) async {
    if (!_ready || !Platform.isAndroid) return;
    const android = AndroidNotificationDetails(
      'gmp_passenger_messages_v2',
      'Ride messages',
      channelDescription: 'Messages from your driver',
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      sound: RawResourceAndroidNotificationSound('gaotus_alert'),
      enableVibration: true,
      visibility: NotificationVisibility.public,
    );
    try {
      await _plugin.show(
        500000 + (bookingId % 499999),
        title,
        body,
        const NotificationDetails(android: android),
        payload: 'chat:$bookingId',
      );
    } catch (_) {}
  }
}
''')

p=root/'lib/state/passenger_session.dart'
s=p.read_text()
if "import '../services/passenger_notification_service.dart';" not in s:
    s=s.replace("import '../services/push_service.dart';\n","import '../services/push_service.dart';\nimport '../services/passenger_notification_service.dart';\n",1)
if 'final PassengerNotificationService _notifications=' not in s:
    s=s.replace('  final PushService _push=PushService();\n','  final PushService _push=PushService();\n  final PassengerNotificationService _notifications=PassengerNotificationService();\n',1)
if 'bool _bookingRefreshInFlight=false;' not in s:
    s=s.replace('  bool _nearbyInFlight=false;\n','  bool _nearbyInFlight=false;\n  bool _bookingRefreshInFlight=false;\n  final Map<int,String> _lastNotifiedStatus=<int,String>{};\n',1)

old_init="""    _realtime.onConnection=(v){realtimeConnected=v;notifyListeners();};
    _realtime.onEvent=(e){final type=e['type']?.toString();if(type=='driver.location'){tracking=DriverTracking.fromJson(<String,dynamic>{'tracking':true,'has_location':true,'signal':'live','status':activeBooking?.status??'assigned',...e}).keepLastLocation(tracking);notifyListeners();}else if(activeBooking!=null){unawaited(refreshBooking(activeBooking!.id,silent:true));}};
    _push.onToken=(v){if(authenticated)unawaited(_registerPush());};
    _push.onMessage=(d){unawaited(refreshBookings(silent:true));if(activeBooking!=null)unawaited(refreshBooking(activeBooking!.id,silent:true));};
"""
new_init="""    _realtime.onConnection=(v){realtimeConnected=v;notifyListeners();};
    _realtime.onEvent=(e){
      final type=e['type']?.toString();
      if(type=='driver.location'){
        tracking=DriverTracking.fromJson(<String,dynamic>{'tracking':true,'has_location':true,'signal':'live','status':activeBooking?.status??'assigned',...e}).keepLastLocation(tracking);
        notifyListeners();
        return;
      }
      final booking=activeBooking;
      if(type=='chat.message'&&booking!=null){
        final message=e['message'];
        final preview=message is Map?(message['message']??'').toString():'';
        unawaited(_notifications.showMessage(bookingId:booking.id,title:'Message from your driver',body:preview.isEmpty?'You have a new ride message.':preview));
      }
      if(booking!=null)unawaited(refreshBooking(booking.id,silent:true));
    };
    _push.onToken=(v){if(authenticated)unawaited(_registerPush());};
    _push.onMessage=(d){
      final bookingId=int.tryParse((d['booking_id']??activeBooking?.id??0).toString())??0;
      final type=(d['event_type']??'').toString();
      final title=(d['notification_title']??'Gaotus Mobility').toString();
      final body=(d['notification_body']??'Your ride has an update.').toString();
      if(bookingId>0){
        if(type=='chat.message')unawaited(_notifications.showMessage(bookingId:bookingId,title:title,body:body));
        else unawaited(_notifications.showRideUpdate(bookingId:bookingId,title:title,body:body));
      }
      unawaited(refreshBookings(silent:true));
      if(activeBooking!=null)unawaited(refreshBooking(activeBooking!.id,silent:true));
    };
"""
if old_init not in s: raise SystemExit('session init callbacks marker missing')
s=s.replace(old_init,new_init,1)

needle='      try { await _push.initialize().timeout(const Duration(seconds:8)); } catch (_) {}\n'
if needle not in s: raise SystemExit('push initialize marker missing')
s=s.replace(needle,'      try { await _notifications.initialize().timeout(const Duration(seconds:4)); } catch (_) {}\n'+needle,1)

s=s.replace('_poll=Timer.periodic(const Duration(seconds:3),(_){','_poll=Timer.periodic(const Duration(seconds:2),(_){',1)

old_refresh_bookings="""  Future<void> refreshBookings({bool silent=false,bool connectRealtime=true,bool propagateErrors=false}) async {if(_api==null)return;if(!silent){busy=true;notifyListeners();}try{final r=await _api!.bookings();final raw=r['bookings'];bookings=raw is List?raw.whereType<Map>().map((e)=>PassengerBooking.fromJson(Map<String,dynamic>.from(e))).toList():<PassengerBooking>[];activeBooking=bookings.cast<PassengerBooking?>().firstWhere((b)=>b?.active==true,orElse:()=>null);if(connectRealtime&&activeBooking!=null)await _connectBooking(activeBooking!.id);}on ApiException catch(e){if(e.statusCode==401||e.statusCode==403)await _clear();else errorMessage=e.message;if(propagateErrors)rethrow;}catch(e){errorMessage='$e';if(propagateErrors)rethrow;}finally{busy=false;notifyListeners();}}
"""
new_refresh_bookings="""  Future<void> refreshBookings({bool silent=false,bool connectRealtime=true,bool propagateErrors=false}) async {if(_api==null)return;if(!silent){busy=true;notifyListeners();}try{final r=await _api!.bookings().timeout(const Duration(seconds:6));final raw=r['bookings'];bookings=raw is List?raw.whereType<Map>().map((e)=>PassengerBooking.fromJson(Map<String,dynamic>.from(e))).toList():<PassengerBooking>[];activeBooking=bookings.cast<PassengerBooking?>().firstWhere((b)=>b?.active==true,orElse:()=>null);notifyListeners();if(connectRealtime&&activeBooking!=null)unawaited(_connectBooking(activeBooking!.id));}on ApiException catch(e){if(e.statusCode==401||e.statusCode==403)await _clear();else errorMessage=e.message;if(propagateErrors)rethrow;}catch(e){errorMessage='$e';if(propagateErrors)rethrow;}finally{busy=false;notifyListeners();}}
"""
if old_refresh_bookings not in s: raise SystemExit('refreshBookings marker missing')
s=s.replace(old_refresh_bookings,new_refresh_bookings,1)

old_refresh_booking="""  Future<void> refreshBooking(int id,{bool silent=false}) async {if(_api==null)return;try{final r=await _api!.booking(id);final b=PassengerBooking.fromJson(Map<String,dynamic>.from(r['booking'] as Map));final i=bookings.indexWhere((x)=>x.id==id);if(i>=0)bookings[i]=b;else bookings.insert(0,b);if(b.active){activeBooking=b;await _connectBooking(id);}else if(activeBooking?.id==id){activeBooking=null;tracking=null;_realtime.unsubscribe(id);}notifyListeners();}catch(e){if(!silent)errorMessage='$e';}}
  Future<void> _connectBooking(int id) async {if(realtimeUrl==null||token==null)return;if(!realtimeConnected)await _realtime.connect(baseUrl:realtimeUrl!,token:token!,bookingId:id);else _realtime.subscribe(id);}
"""
new_refresh_booking="""  Future<void> refreshBooking(int id,{bool silent=false}) async {
    if(_api==null||_bookingRefreshInFlight)return;
    _bookingRefreshInFlight=true;
    try{
      PassengerBooking? previous;
      for(final item in bookings){if(item.id==id){previous=item;break;}}
      final r=await _api!.booking(id).timeout(const Duration(seconds:5));
      final b=PassengerBooking.fromJson(Map<String,dynamic>.from(r['booking'] as Map));
      final i=bookings.indexWhere((x)=>x.id==id);
      if(i>=0)bookings[i]=b;else bookings.insert(0,b);
      if(b.active){
        activeBooking=b;
        notifyListeners();
        unawaited(_connectBooking(id));
      }else if(activeBooking?.id==id){
        activeBooking=null;tracking=null;_realtime.unsubscribe(id);notifyListeners();
      }else{
        notifyListeners();
      }
      final before=previous?.status.toLowerCase();
      final after=b.status.toLowerCase();
      if(before!=null&&before!=after&&_lastNotifiedStatus[id]!=after){
        _lastNotifiedStatus[id]=after;
        final labels=<String,String>{
          'assigned':'Driver assigned',
          'enroute':'Driver on the way',
          'arrived':'Driver has arrived',
          'pob':'Trip started',
          'completed':'Trip completed',
          'cancelled':'Ride cancelled',
        };
        final title=labels[after];
        if(title!=null)unawaited(_notifications.showRideUpdate(bookingId:id,title:title,body:_statusNotificationBody(after)));
      }
    }catch(e){
      if(!silent)errorMessage='$e';
    }finally{
      _bookingRefreshInFlight=false;
    }
  }

  String _statusNotificationBody(String status){
    switch(status){
      case 'assigned': return 'Your driver has accepted the ride.';
      case 'enroute': return 'Your driver is travelling to the pickup point.';
      case 'arrived': return 'Your driver is waiting at the pickup point.';
      case 'pob': return 'Your trip is now in progress.';
      case 'completed': return 'Thanks for riding with us.';
      case 'cancelled': return 'Your ride has been cancelled.';
      default: return 'Your ride status has changed.';
    }
  }

  Future<void> _connectBooking(int id) async {
    if(realtimeUrl==null||token==null)return;
    if(!realtimeConnected){
      unawaited(_realtime.connect(baseUrl:realtimeUrl!,token:token!,bookingId:id));
    }else{
      _realtime.subscribe(id);
    }
  }
"""
if old_refresh_booking not in s: raise SystemExit('refreshBooking/connect marker missing')
s=s.replace(old_refresh_booking,new_refresh_booking,1)

s=s.replace("now.difference(_lastWordPressTracking!)<const Duration(seconds:12)","now.difference(_lastWordPressTracking!)<const Duration(seconds:4)",1)

old_create="""  Future<PassengerBooking> createBooking(VehicleQuote vehicle,{String paymentMethod='online'}) async {if(_api==null||lastQuoteRequest==null)throw const ApiException('Request a fare first.');final body=<String,Object?>{...lastQuoteRequest!,'vehicle_id':vehicle.id,'payment_method':paymentMethod,'terms_accept':true};busy=true;notifyListeners();try{final r=await _api!.createBooking(body);final b=PassengerBooking.fromJson(Map<String,dynamic>.from(r['booking'] as Map));bookings.insert(0,b);activeBooking=b;await _connectBooking(b.id);return b;}finally{busy=false;notifyListeners();}}
"""
new_create="""  Future<PassengerBooking> createBooking(VehicleQuote vehicle,{String paymentMethod='online'}) async {if(_api==null||lastQuoteRequest==null)throw const ApiException('Request a fare first.');final body=<String,Object?>{...lastQuoteRequest!,'vehicle_id':vehicle.id,'payment_method':paymentMethod,'terms_accept':true};busy=true;notifyListeners();try{final r=await _api!.createBooking(body).timeout(const Duration(seconds:12));final b=PassengerBooking.fromJson(Map<String,dynamic>.from(r['booking'] as Map));bookings.insert(0,b);activeBooking=b;notifyListeners();unawaited(_connectBooking(b.id));unawaited(refreshBooking(b.id,silent:true));return b;}finally{busy=false;notifyListeners();}}
"""
if old_create not in s: raise SystemExit('createBooking marker missing')
s=s.replace(old_create,new_create,1)
p.write_text(s)

p=root/'lib/screens/home_screen.dart'
s=p.read_text()
s=s.replace('width:58,height:64,child:_NearbyCarMarker(car:car)','width:48,height:52,child:_NearbyCarMarker(car:car)')
idx=s.rfind('class _NearbyCarMarker')
if idx<0: raise SystemExit('home nearby marker class missing')
tail=s[idx:].replace('size: 48,','size: 38,',1)
s=s[:idx]+tail
s=s.replace('Passenger v0.5.5','Passenger v0.5.6')
p.write_text(s)

p=root/'lib/screens/quote_screen.dart'
s=p.read_text()
s=s.replace('width:58,height:64,child:_QuoteNearbyCar(car:car)','width:48,height:52,child:_QuoteNearbyCar(car:car)')
idx=s.rfind('class _QuoteNearbyCar')
if idx<0: raise SystemExit('quote car marker class missing')
tail=s[idx:].replace('size:48,','size:38,',1)
s=s[:idx]+tail
p.write_text(s)

p=root/'lib/screens/trip_screen.dart'
s=p.read_text()
if "import '../widgets/premium_car_marker.dart';" not in s:
    s=s.replace("import '../widgets/premium.dart';\n","import '../widgets/premium.dart';\nimport '../widgets/premium_car_marker.dart';\n",1)
if "import 'dart:async';" not in s:
    s=s.replace("import 'package:flutter/material.dart';\n","import 'dart:async';\n\nimport 'package:flutter/material.dart';\n",1)
if 'Timer? criticalPoll;' not in s:
    s=s.replace('  double? lastDriverLat, lastDriverLng;\n','  double? lastDriverLat, lastDriverLng;\n  Timer? criticalPoll;\n',1)

old_trip_init="""    widget.session.addListener(_sessionChanged);
    widget.session.refreshBooking(widget.bookingId, silent: true);
    widget.session.refreshTracking(widget.bookingId);
"""
new_trip_init="""    widget.session.addListener(_sessionChanged);
    widget.session.refreshBooking(widget.bookingId, silent: true);
    widget.session.refreshTracking(widget.bookingId);
    criticalPoll=Timer.periodic(const Duration(seconds:2),(_){
      unawaited(widget.session.refreshBooking(widget.bookingId,silent:true));
      unawaited(widget.session.refreshTracking(widget.bookingId));
    });
"""
if old_trip_init not in s: raise SystemExit('trip init marker missing')
s=s.replace(old_trip_init,new_trip_init,1)
s=s.replace('    widget.session.removeListener(_sessionChanged);\n    super.dispose();','    criticalPoll?.cancel();\n    widget.session.removeListener(_sessionChanged);\n    super.dispose();',1)
s=s.replace("if (driverPoint != null) Marker(point: driverPoint, width: 58, height: 58, child: _DriverMarker(live: tracking?.signal == 'live')),","if (driverPoint != null) Marker(point: driverPoint, width: 50, height: 54, child: PremiumCarMarker(headingDegrees:tracking?.heading??0,size:40,accent:tracking?.signal=='delayed'?const Color(0xFF6B7280):AppTheme.ink,selected:true,dimmed:tracking?.signal=='lost')),",1)

start=s.find('class _DriverMarker extends StatelessWidget {')
if start>=0:
    end=s.find('\nclass _TrackingBanner extends StatelessWidget {',start)
    if end<0: raise SystemExit('tracking banner marker missing')
    s=s[:start]+s[end+1:]
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.6+17','flutter_local_notifications','assets/audio/gaotus_alert.mp3'],
  'lib/config/app_config.dart':["version = '0.5.6'"],
  'lib/services/passenger_notification_service.dart':['RawResourceAndroidNotificationSound','gaotus_alert'],
  'lib/state/passenger_session.dart':['_bookingRefreshInFlight','unawaited(_connectBooking','Duration(seconds:4)','_notifications.showRideUpdate'],
  'lib/screens/home_screen.dart':['Passenger v0.5.6','size: 38'],
  'lib/screens/quote_screen.dart':['size:38'],
  'lib/screens/trip_screen.dart':['PremiumCarMarker(','criticalPoll=Timer.periodic','size:40'],
  'tool/bootstrap_platforms.sh':['android/app/src/main/res/raw/gaotus_alert.mp3'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
if asset.stat().st_size<4000: raise SystemExit('sound asset unexpectedly small')
print('Passenger v0.5.6 assigned-car + connection + sound patch applied')
