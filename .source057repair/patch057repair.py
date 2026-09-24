from pathlib import Path

root=Path('passenger')

# Repair the v0.5.7 realtime service after the generated patch duplicated a block.
(root/'lib/services/realtime_service.dart').write_text(r'''import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

final class PassengerRealtimeService {
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _sub;
  Timer? _retry;
  Timer? _heartbeat;
  Timer? _watchdog;
  String? _baseUrl, _token;
  int _bookingId = 0;
  bool _opening = false;
  bool _connected = false;
  DateTime? _lastAttempt;
  DateTime? _lastMessage;
  final http.Client _http = http.Client();
  void Function(bool connected)? onConnection;
  void Function(Map<String,dynamic> event)? onEvent;

  Future<void> connect({required String baseUrl, required String token, int bookingId=0}) async {
    _baseUrl=_normalize(baseUrl);_token=token;_bookingId=bookingId;
    final now=DateTime.now();
    if(_opening)return;
    if(_lastAttempt!=null&&now.difference(_lastAttempt!)<const Duration(seconds:2))return;
    _opening=true;_lastAttempt=now;
    await disconnect(scheduleRetry:false);
    try {
      var url=_baseUrl!; if(!url.endsWith('/ws')) url='$url/ws';
      final input=Uri.parse(url);
      final uri=input.replace(
        scheme:input.scheme=='https'?'wss':input.scheme=='http'?'ws':input.scheme,
        queryParameters:<String,String>{'token':token},
      );
      _channel=WebSocketChannel.connect(uri);
      await _channel!.ready.timeout(const Duration(seconds:8));
      _lastMessage=DateTime.now();
      _sub=_channel!.stream.listen(_message,onDone:_lost,onError:(_)=>_lost(),cancelOnError:true);
      _heartbeat=Timer.periodic(const Duration(seconds:15),(_)=>_ping());
      _watchdog=Timer.periodic(const Duration(seconds:10),(_){
        final last=_lastMessage;
        if(last!=null&&DateTime.now().difference(last)>const Duration(seconds:35))_lost();
      });
      if(_bookingId>0) subscribe(_bookingId);
    } catch (_) {
      _setConnected(false);
      await _closeOnly();
      _schedule();
    } finally {
      _opening=false;
    }
  }

  String _normalize(String value){var out=value.trim();while(out.endsWith('/'))out=out.substring(0,out.length-1);return out;}
  Uri _httpUri(String path)=>Uri.parse('${_baseUrl!}${path.startsWith('/')?path:'/$path'}');

  void _setConnected(bool value){
    if(_connected==value)return;
    _connected=value;
    onConnection?.call(value);
  }

  void _message(dynamic raw){
    try{
      final x=jsonDecode(raw.toString());
      if(x is! Map)return;
      _lastMessage=DateTime.now();
      final event=Map<String,dynamic>.from(x);
      if(event['type']=='auth.ok'||event['type']=='pong')_setConnected(true);
      onEvent?.call(event);
    }catch(_){}
  }

  void _ping(){
    try{_channel?.sink.add(jsonEncode(<String,Object?>{'type':'ping'}));}catch(_){_lost();}
  }

  void subscribe(int id){_bookingId=id;try{_channel?.sink.add(jsonEncode(<String,Object?>{'type':'subscribe.booking','booking_id':id}));}catch(_){}}
  void unsubscribe(int id){try{_channel?.sink.add(jsonEncode(<String,Object?>{'type':'unsubscribe.booking','booking_id':id}));}catch(_){}if(_bookingId==id)_bookingId=0;}

  void _lost(){_setConnected(false);unawaited(_recover());}
  Future<void> _recover() async{await _closeOnly();_schedule();}

  void _schedule(){
    _retry?.cancel();
    if(_baseUrl==null||_token==null)return;
    _retry=Timer(const Duration(seconds:3),()=>connect(baseUrl:_baseUrl!,token:_token!,bookingId:_bookingId));
  }

  Future<Map<String,dynamic>?> pollNearby(double lat,double lng,{double radiusKm=12,int limit=16}) async {
    if(_baseUrl==null||_baseUrl!.isEmpty||_token==null||_token!.isEmpty)return null;
    try{
      final response=await _http.post(
        _httpUri('/http/passenger/nearby'),
        headers:const <String,String>{'Accept':'application/json','Content-Type':'application/json'},
        body:jsonEncode(<String,Object?>{'token':_token,'lat':lat,'lng':lng,'radius_km':radiusKm,'limit':limit}),
      ).timeout(const Duration(seconds:4));
      if(response.statusCode<200||response.statusCode>=300)return null;
      final decoded=jsonDecode(response.body);
      return decoded is Map?Map<String,dynamic>.from(decoded):null;
    }catch(_){return null;}
  }

  Future<Map<String,dynamic>?> pollBookingLive(int bookingId) async {
    if(_baseUrl==null||_baseUrl!.isEmpty||_token==null||_token!.isEmpty)return null;
    try{
      final response=await _http.post(
        _httpUri('/http/booking/$bookingId/live'),
        headers:const <String,String>{'Accept':'application/json','Content-Type':'application/json'},
        body:jsonEncode(<String,Object?>{'token':_token}),
      ).timeout(const Duration(seconds:4));
      if(response.statusCode<200||response.statusCode>=300)return null;
      final decoded=jsonDecode(response.body);
      return decoded is Map?Map<String,dynamic>.from(decoded):null;
    }catch(_){return null;}
  }

  Future<void> _closeOnly() async{
    _heartbeat?.cancel();_heartbeat=null;
    _watchdog?.cancel();_watchdog=null;
    await _sub?.cancel();_sub=null;
    try{await _channel?.sink.close();}catch(_){}
    _channel=null;
    _setConnected(false);
  }

  Future<void> disconnect({bool scheduleRetry=false}) async{
    _retry?.cancel();_retry=null;
    await _closeOnly();
    if(scheduleRetry)_schedule();
  }

  Future<void> dispose() async{await disconnect();_http.close();}
}
''')

p=root/'lib/state/passenger_session.dart'
s=p.read_text().replace('_nearbyLastGoodAt','_lastNearbyGoodAt')
p.write_text(s)

checks={
 'lib/services/realtime_service.dart':['class PassengerRealtimeService','pollNearby','pollBookingLive','_watchdog','Duration(seconds:3)'],
 'lib/state/passenger_session.dart':['_lastNearbyGoodAt','refreshLiveSnapshot','_nearbyEmptyStreak'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
print('Passenger v0.5.7 realtime repair applied')
