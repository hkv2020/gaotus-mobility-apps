from pathlib import Path

root = Path("passenger")

def replace_one(path, old, new, label):
    p = root / path
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"{label} marker missing in {path}")
    p.write_text(s.replace(old, new, 1))

replace_one("pubspec.yaml", "version: 0.5.2+13", "version: 0.5.3+14", "pubspec version")
replace_one("lib/config/app_config.dart", "static const version = '0.5.2';", "static const version = '0.5.3';", "app version")

(root / "lib/models/nearby_car.dart").write_text("""final class NearbyCar {
  const NearbyCar({
    required this.lat,
    required this.lng,
    this.heading,
    this.distanceKm,
    this.age,
    this.signal = 'live',
  });

  final double lat;
  final double lng;
  final double? heading;
  final double? distanceKm;
  final int? age;
  final String signal;

  factory NearbyCar.fromJson(Map<String,dynamic> json) {
    double? number(Object? value) => value is num ? value.toDouble() : double.tryParse((value ?? '').toString());
    int? integer(Object? value) => value is num ? value.toInt() : int.tryParse((value ?? '').toString());
    return NearbyCar(
      lat: number(json['lat']) ?? 0,
      lng: number(json['lng']) ?? 0,
      heading: number(json['heading']),
      distanceKm: number(json['distance_km']),
      age: integer(json['age']),
      signal: (json['signal'] ?? 'live').toString(),
    );
  }

  bool get valid => lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180 && (lat != 0 || lng != 0);
}
""")

# API fallback
p = root / "lib/core/api_client.dart"
s = p.read_text()
marker = "  Future<Map<String,dynamic>> quote(Map<String,Object?> body) => request('POST','/customer/quote',body:body);\n"
if marker not in s:
    raise SystemExit("api quote marker missing")
s = s.replace(marker, marker + "  Future<Map<String,dynamic>> nearbyDrivers(double lat,double lng,{double radiusKm=8,int limit=12}) => request('POST','/customer/nearby-drivers',body:{'lat':lat,'lng':lng,'radius_km':radiusKm,'limit':limit});\n", 1)
p.write_text(s)

# Realtime nearby recovery + faster reconnect.
p = root / "lib/services/realtime_service.dart"
s = p.read_text()
s = s.replace("now.difference(_lastAttempt!)<const Duration(seconds:25)", "now.difference(_lastAttempt!)<const Duration(seconds:5)")
s = s.replace("_retry=Timer(const Duration(seconds:30)", "_retry=Timer(const Duration(seconds:6)")
marker = "  Future<Map<String,dynamic>?> pollBookingLive(int bookingId) async {\n"
if marker not in s:
    raise SystemExit("passenger realtime live marker missing")
nearby_method = """  Future<Map<String,dynamic>?> pollNearby(double lat,double lng,{double radiusKm=8,int limit=12}) async {
    if(_baseUrl==null||_baseUrl!.isEmpty||_token==null||_token!.isEmpty)return null;
    try{
      final response=await _http.post(
        _httpUri('/http/passenger/nearby'),
        headers:const <String,String>{'Accept':'application/json','Content-Type':'application/json'},
        body:jsonEncode(<String,Object?>{'token':_token,'lat':lat,'lng':lng,'radius_km':radiusKm,'limit':limit}),
      ).timeout(const Duration(seconds:5));
      if(response.statusCode<200||response.statusCode>=300)return null;
      final decoded=jsonDecode(response.body);
      return decoded is Map?Map<String,dynamic>.from(decoded):null;
    }catch(_){return null;}
  }

"""
s = s.replace(marker, nearby_method + marker, 1)
p.write_text(s)

# Passenger session.
p = root / "lib/state/passenger_session.dart"
s = p.read_text()
s = s.replace("import '../models/tracking.dart';\n", "import '../models/tracking.dart';\nimport '../models/nearby_car.dart';\n", 1)
s = s.replace("  DateTime? _lastWordPressTracking;\n", "  DateTime? _lastWordPressTracking;\n  DateTime? _lastNearbyWordPress;\n", 1)
s = s.replace("  DriverTracking? tracking;\n", "  DriverTracking? tracking;\n  List<NearbyCar> nearbyCars=<NearbyCar>[];\n", 1)
old_poll = """  void _startPoll(){
    _poll?.cancel();
    _poll=Timer.periodic(const Duration(seconds:12),(_){
      if(activeBooking!=null){unawaited(refreshBooking(activeBooking!.id,silent:true));}
      else{unawaited(refreshBookings(silent:true));}
    });
    _livePoll?.cancel();
    _livePoll=Timer.periodic(const Duration(seconds:3),(_){
      final booking=activeBooking;
      if(booking!=null&&!realtimeConnected)unawaited(_refreshRealtimeTracking(booking.id));
    });
  }
"""
new_poll = """  void _startPoll(){
    _poll?.cancel();
    _poll=Timer.periodic(const Duration(seconds:3),(_){
      if(activeBooking!=null){unawaited(refreshBooking(activeBooking!.id,silent:true));}
      else{unawaited(refreshBookings(silent:true));}
    });
    _livePoll?.cancel();
    _livePoll=Timer.periodic(const Duration(seconds:2),(_){
      final booking=activeBooking;
      if(booking!=null)unawaited(_refreshRealtimeTracking(booking.id));
    });
  }
"""
if old_poll not in s:
    raise SystemExit("passenger poll block missing")
s = s.replace(old_poll, new_poll, 1)

chat_marker = "  Future<List<ChatMessage>> chatMessages(int bookingId,{int afterId=0,bool markRead=true}) async {\n"
if chat_marker not in s:
    raise SystemExit("chat marker missing")
nearby_session = """  Future<void> refreshNearby(double lat,double lng,{double radiusKm=8,int limit=12}) async {
    if(!authenticated||_api==null)return;
    Map<String,dynamic>? data;
    if(realtimeUrl!=null&&realtimeUrl!.isNotEmpty){
      data=await _realtime.pollNearby(lat,lng,radiusKm:radiusKm,limit:limit);
    }
    if(data==null){
      final now=DateTime.now();
      if(_lastNearbyWordPress!=null&&now.difference(_lastNearbyWordPress!)<const Duration(seconds:10))return;
      _lastNearbyWordPress=now;
      try{data=await _api!.nearbyDrivers(lat,lng,radiusKm:radiusKm,limit:limit);}catch(_){return;}
    }
    final raw=data['cars'];
    if(raw is List){
      nearbyCars=raw.whereType<Map>().map((e)=>NearbyCar.fromJson(Map<String,dynamic>.from(e))).where((e)=>e.valid).toList();
      notifyListeners();
    }
  }

"""
s = s.replace(chat_marker, nearby_session + chat_marker, 1)
s = s.replace("activeBooking=null;tracking=null;await _store.clearSession();", "activeBooking=null;tracking=null;nearbyCars=<NearbyCar>[];await _store.clearSession();")
p.write_text(s)

# Home: nearby markers + polling.
p = root / "lib/screens/home_screen.dart"
s = p.read_text()
if not s.startswith("import 'dart:async';"):
    s = "import 'dart:async';\n\n" + s
s = s.replace("import '../models/place_selection.dart';\n", "import '../models/place_selection.dart';\nimport '../models/nearby_car.dart';\n", 1)
s = s.replace("  final map = MapController();\n", "  final map = MapController();\n  Timer? nearbyTimer;\n", 1)
old_init = """  @override
  void initState() {
    super.initState();
    pickup.text = 'Current location';
    WidgetsBinding.instance.addPostFrameCallback((_) => _primeLocation());
  }
"""
new_init = """  @override
  void initState() {
    super.initState();
    pickup.text = 'Current location';
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _primeLocation();
      nearbyTimer=Timer.periodic(const Duration(seconds:4),(_)=>unawaited(_refreshNearby()));
    });
  }

  @override
  void dispose() {
    nearbyTimer?.cancel();
    pickup.dispose();
    dropoff.dispose();
    super.dispose();
  }

  Future<void> _refreshNearby() async {
    if(!mounted||widget.session.activeBooking!=null)return;
    final lat=pickupLat??center.latitude;
    final lng=pickupLng??center.longitude;
    await widget.session.refreshNearby(lat,lng);
  }
"""
if old_init not in s:
    raise SystemExit("home init block missing")
s = s.replace(old_init, new_init, 1)
s = s.replace("      map.move(here, 15.5);\n", "      map.move(here, 15.5);\n      unawaited(widget.session.refreshNearby(p.latitude,p.longitude));\n", 1)
s = s.replace("      map.move(LatLng(selected.lat, selected.lng), 16);\n", "      map.move(LatLng(selected.lat, selected.lng), 16);\n      unawaited(widget.session.refreshNearby(selected.lat,selected.lng));\n", 1)
old_markers = """    final pickupMarker = pickupLat != null && pickupLng != null
        ? <Marker>[Marker(point: LatLng(pickupLat!, pickupLng!), width: 42, height: 42, child: const Icon(Icons.my_location, color: Colors.blue, size: 26))]
        : <Marker>[];
"""
new_markers = """    final pickupMarker = pickupLat != null && pickupLng != null
        ? <Marker>[Marker(point: LatLng(pickupLat!, pickupLng!), width: 42, height: 42, child: const Icon(Icons.my_location, color: Colors.blue, size: 26))]
        : <Marker>[];
    final nearbyMarkers = s.activeBooking==null
        ? s.nearbyCars.map((car)=>Marker(point:LatLng(car.lat,car.lng),width:42,height:42,child:_NearbyCarMarker(car:car))).toList()
        : <Marker>[];
"""
if old_markers not in s:
    raise SystemExit("home marker block missing")
s = s.replace(old_markers, new_markers, 1)
s = s.replace("                MarkerLayer(markers: pickupMarker),", "                MarkerLayer(markers: <Marker>[...nearbyMarkers,...pickupMarker]),", 1)
# menu version
s = s.replace("Passenger v0.5.2", "Passenger v0.5.3")
s = s.replace("Passenger ride catalog + grouped ride options", "Live nearby cars + automatic realtime ride updates")
# add marker widget before EOF after class
s += """

class _NearbyCarMarker extends StatelessWidget {
  const _NearbyCarMarker({required this.car});
  final NearbyCar car;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
          border: Border.all(color: const Color(0xFF0A0A0A), width: 2),
          boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x33000000), blurRadius: 8)],
        ),
        child: const Icon(Icons.local_taxi_rounded, size: 24, color: Color(0xFF0A0A0A)),
      );
}
"""
p.write_text(s)

# Quote: show nearby cars around pickup while selecting a ride.
p = root / "lib/screens/quote_screen.dart"
s = p.read_text()
if not s.startswith("import 'dart:async';"):
    s = "import 'dart:async';\n\n" + s
s = s.replace("import '../models/place_selection.dart';\n", "import '../models/place_selection.dart';\nimport '../models/nearby_car.dart';\n", 1)
s = s.replace("  late FareQuote currentQuote;\n", "  late FareQuote currentQuote;\n  Timer? nearbyTimer;\n", 1)
old_q_init = """  @override void initState(){
    super.initState();
    currentQuote=widget.quote;
    if(currentQuote.vehicles.isNotEmpty)selected=currentQuote.vehicles.first;
  }
"""
new_q_init = """  @override void initState(){
    super.initState();
    currentQuote=widget.quote;
    if(currentQuote.vehicles.isNotEmpty)selected=currentQuote.vehicles.first;
    widget.session.addListener(_sessionChanged);
    WidgetsBinding.instance.addPostFrameCallback((_){
      _refreshNearby();
      nearbyTimer=Timer.periodic(const Duration(seconds:4),(_)=>unawaited(_refreshNearby()));
    });
  }

  void _sessionChanged(){if(mounted)setState((){});}

  Future<void> _refreshNearby() async{
    final j=currentQuote.journey;
    final point=_point(j['pickup_lat'],j['pickup_lng']);
    if(point!=null)await widget.session.refreshNearby(point.latitude,point.longitude);
  }

  @override void dispose(){
    nearbyTimer?.cancel();
    widget.session.removeListener(_sessionChanged);
    super.dispose();
  }
"""
if old_q_init not in s:
    raise SystemExit("quote init marker missing")
s = s.replace(old_q_init, new_q_init, 1)
old_q_mark = """    final markers=<Marker>[
      if(pickup!=null)Marker(point:pickup,width:48,height:48,child:const _MapPin(icon:Icons.circle,dark:true)),
      if(dropoff!=null)Marker(point:dropoff,width:48,height:48,child:const _MapPin(icon:Icons.stop_rounded,dark:false)),
    ];
"""
new_q_mark = """    final markers=<Marker>[
      ...widget.session.nearbyCars.map((car)=>Marker(point:LatLng(car.lat,car.lng),width:42,height:42,child:_QuoteNearbyCar(car:car))),
      if(pickup!=null)Marker(point:pickup,width:48,height:48,child:const _MapPin(icon:Icons.circle,dark:true)),
      if(dropoff!=null)Marker(point:dropoff,width:48,height:48,child:const _MapPin(icon:Icons.stop_rounded,dark:false)),
    ];
"""
if old_q_mark not in s:
    raise SystemExit("quote markers missing")
s = s.replace(old_q_mark, new_q_mark, 1)
s += """

class _QuoteNearbyCar extends StatelessWidget{
  const _QuoteNearbyCar({required this.car});
  final NearbyCar car;
  @override Widget build(BuildContext context)=>Container(
    decoration:BoxDecoration(color:Colors.white,shape:BoxShape.circle,border:Border.all(color:AppTheme.ink,width:2),boxShadow:const <BoxShadow>[BoxShadow(color:Color(0x33000000),blurRadius:8)]),
    child:const Icon(Icons.local_taxi_rounded,size:24,color:AppTheme.ink),
  );
}
"""
p.write_text(s)

# Assertions
checks = {
    "pubspec.yaml": ["version: 0.5.3+14"],
    "lib/state/passenger_session.dart": ["refreshNearby", "Duration(seconds:2)", "nearbyCars"],
    "lib/screens/home_screen.dart": ["_NearbyCarMarker", "Timer.periodic(const Duration(seconds:4)", "Passenger v0.5.3"],
    "lib/screens/quote_screen.dart": ["_QuoteNearbyCar", "widget.session.nearbyCars"],
    "lib/services/realtime_service.dart": ["pollNearby", "Duration(seconds:6)"],
}
for path, needles in checks.items():
    text = (root / path).read_text()
    for needle in needles:
        if needle not in text:
            raise SystemExit(f"missing {needle} in {path}")

print("Passenger v0.5.3 live nearby/realtime patch applied")
