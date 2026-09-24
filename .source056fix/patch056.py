from pathlib import Path

root=Path('passenger')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.5+16','version: 0.5.6+17','version')
replace_one('lib/config/app_config.dart',"static const version = '0.5.5';","static const version = '0.5.6';",'app version')

# Smaller premium cars + use the premium car everywhere relevant in Passenger.
p=root/'lib/screens/home_screen.dart'
s=p.read_text()
s=s.replace("width:58,height:64,child:_NearbyCarMarker(car:car)","width:48,height:52,child:_NearbyCarMarker(car:car)")
s=s.replace("        size: 48,","        size: 38,",1)
s=s.replace("const CircleAvatar(backgroundColor: AppTheme.accent, child: Icon(Icons.local_taxi_rounded, color: AppTheme.ink))",
"""SizedBox(
                            width: 40,
                            height: 42,
                            child: PremiumCarMarker(
                              headingDegrees: widget.session.tracking?.heading ?? 0,
                              size: 32,
                              accent: AppTheme.accent,
                              selected: true,
                            ),
                          )""",1)
s=s.replace('Passenger v0.5.5','Passenger v0.5.6')
p.write_text(s)

p=root/'lib/screens/quote_screen.dart'
s=p.read_text()
s=s.replace("width:58,height:64,child:_QuoteNearbyCar(car:car)","width:48,height:52,child:_QuoteNearbyCar(car:car)")
s=s.replace("    size:48,","    size:38,",1)
old="""          SizedBox(width:88,height:62,child:vehicle.image.isNotEmpty
            ?Image.network(vehicle.image,fit:BoxFit.contain,errorBuilder:(_,__,___)=>const Icon(Icons.local_taxi_rounded,size:48))
            :const Icon(Icons.local_taxi_rounded,size:48)),"""
new="""          SizedBox(
            width:88,
            height:62,
            child:vehicle.image.isNotEmpty
              ?Image.network(
                  vehicle.image,
                  fit:BoxFit.contain,
                  errorBuilder:(_,__,___)=>const PremiumCarMarker(headingDegrees:0,size:42,accent:AppTheme.ink),
                )
              :const PremiumCarMarker(headingDegrees:0,size:42,accent:AppTheme.ink),
          ),"""
if old not in s: raise SystemExit('vehicle fallback marker missing')
s=s.replace(old,new,1)
p.write_text(s)

p=root/'lib/screens/trip_screen.dart'
s=p.read_text()
if "import '../widgets/premium_car_marker.dart';" not in s:
    marker="import '../widgets/premium.dart';\n"
    if marker not in s: raise SystemExit('trip premium import marker missing')
    s=s.replace(marker,marker+"import '../widgets/premium_car_marker.dart';\n",1)
s=s.replace(
"if (driverPoint != null) Marker(point: driverPoint, width: 58, height: 58, child: _DriverMarker(live: tracking?.signal == 'live')),",
"if (driverPoint != null) Marker(point: driverPoint, width: 50, height: 54, child: _DriverMarker(live: tracking?.signal == 'live', heading: tracking?.heading ?? 0)),",
1)
old="""class _DriverMarker extends StatelessWidget {
  const _DriverMarker({required this.live});
  final bool live;
  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(color: Colors.white, shape: BoxShape.circle, border: Border.all(color: live ? AppTheme.success : AppTheme.softInk, width: 2.5), boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x33000000), blurRadius: 10)]),
        child: const Icon(Icons.local_taxi_rounded, color: AppTheme.ink, size: 31),
      );
}
"""
new="""class _DriverMarker extends StatelessWidget {
  const _DriverMarker({required this.live, required this.heading});
  final bool live;
  final double heading;
  @override
  Widget build(BuildContext context) => PremiumCarMarker(
        headingDegrees: heading,
        size: 40,
        accent: live ? AppTheme.success : AppTheme.ink,
        selected: live,
        dimmed: !live,
      );
}
"""
if old not in s: raise SystemExit('trip driver marker class missing')
s=s.replace(old,new,1)
p.write_text(s)

# Ride lifecycle self-heal: never let WebSocket setup block booking UI/status refresh.
p=root/'lib/state/passenger_session.dart'
s=p.read_text()
if 'bool _bookingRefreshInFlight=false;' not in s:
    s=s.replace('  bool _nearbyInFlight=false;\n','  bool _nearbyInFlight=false;\n  bool _bookingRefreshInFlight=false;\n  DateTime? _lastIdleBookingsPoll;\n',1)

old="_realtime.onConnection=(v){realtimeConnected=v;notifyListeners();};"
new="_realtime.onConnection=(v){realtimeConnected=v;notifyListeners();if(v&&activeBooking!=null)unawaited(refreshBooking(activeBooking!.id,silent:true));};"
if old not in s: raise SystemExit('realtime connection callback missing')
s=s.replace(old,new,1)

old="""  void _startPoll(){
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
new="""  void _startPoll(){
    _poll?.cancel();
    _poll=Timer.periodic(const Duration(seconds:1),(_){
      final booking=activeBooking;
      if(booking!=null){
        unawaited(refreshBooking(booking.id,silent:true));
      }else{
        final now=DateTime.now();
        if(_lastIdleBookingsPoll==null||now.difference(_lastIdleBookingsPoll!)>=const Duration(seconds:5)){
          _lastIdleBookingsPoll=now;
          unawaited(refreshBookings(silent:true));
        }
      }
    });
    _livePoll?.cancel();
    _livePoll=Timer.periodic(const Duration(milliseconds:1500),(_){
      final booking=activeBooking;
      if(booking!=null)unawaited(_refreshRealtimeTracking(booking.id));
    });
  }
"""
if old not in s: raise SystemExit('poll block missing')
s=s.replace(old,new,1)

old="  Future<void> refreshBookings({bool silent=false,bool connectRealtime=true,bool propagateErrors=false}) async {if(_api==null)return;if(!silent){busy=true;notifyListeners();}try{final r=await _api!.bookings();final raw=r['bookings'];bookings=raw is List?raw.whereType<Map>().map((e)=>PassengerBooking.fromJson(Map<String,dynamic>.from(e))).toList():<PassengerBooking>[];activeBooking=bookings.cast<PassengerBooking?>().firstWhere((b)=>b?.active==true,orElse:()=>null);if(connectRealtime&&activeBooking!=null)await _connectBooking(activeBooking!.id);}on ApiException catch(e){if(e.statusCode==401||e.statusCode==403)await _clear();else errorMessage=e.message;if(propagateErrors)rethrow;}catch(e){errorMessage='$e';if(propagateErrors)rethrow;}finally{busy=false;notifyListeners();}}"
new="  Future<void> refreshBookings({bool silent=false,bool connectRealtime=true,bool propagateErrors=false}) async {if(_api==null)return;if(!silent){busy=true;notifyListeners();}try{final r=await _api!.bookings();final raw=r['bookings'];bookings=raw is List?raw.whereType<Map>().map((e)=>PassengerBooking.fromJson(Map<String,dynamic>.from(e))).toList():<PassengerBooking>[];activeBooking=bookings.cast<PassengerBooking?>().firstWhere((b)=>b?.active==true,orElse:()=>null);notifyListeners();if(connectRealtime&&activeBooking!=null)unawaited(_connectBooking(activeBooking!.id));}on ApiException catch(e){if(e.statusCode==401||e.statusCode==403)await _clear();else errorMessage=e.message;if(propagateErrors)rethrow;}catch(e){errorMessage='$e';if(propagateErrors)rethrow;}finally{busy=false;notifyListeners();}}"
if old not in s: raise SystemExit('refreshBookings contract missing')
s=s.replace(old,new,1)

old="  Future<void> refreshBooking(int id,{bool silent=false}) async {if(_api==null)return;try{final r=await _api!.booking(id);final b=PassengerBooking.fromJson(Map<String,dynamic>.from(r['booking'] as Map));final i=bookings.indexWhere((x)=>x.id==id);if(i>=0)bookings[i]=b;else bookings.insert(0,b);if(b.active){activeBooking=b;await _connectBooking(id);}else if(activeBooking?.id==id){activeBooking=null;tracking=null;_realtime.unsubscribe(id);}notifyListeners();}catch(e){if(!silent)errorMessage='$e';}}"
new="""  Future<void> refreshBooking(int id,{bool silent=false}) async {
    if(_api==null||_bookingRefreshInFlight)return;
    _bookingRefreshInFlight=true;
    try{
      final r=await _api!.booking(id).timeout(const Duration(seconds:6));
      final raw=r['booking'];
      if(raw is! Map)return;
      final b=PassengerBooking.fromJson(Map<String,dynamic>.from(raw));
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
    }catch(e){
      if(!silent)errorMessage='$e';
    }finally{
      _bookingRefreshInFlight=false;
    }
  }"""
if old not in s: raise SystemExit('refreshBooking contract missing')
s=s.replace(old,new,1)

old="  Future<void> _connectBooking(int id) async {if(realtimeUrl==null||token==null)return;if(!realtimeConnected)await _realtime.connect(baseUrl:realtimeUrl!,token:token!,bookingId:id);else _realtime.subscribe(id);}"
new="""  Future<void> _connectBooking(int id) async {
    if(realtimeUrl==null||token==null)return;
    try{
      if(!realtimeConnected){
        await _realtime.connect(baseUrl:realtimeUrl!,token:token!,bookingId:id).timeout(const Duration(seconds:4));
      }else{
        _realtime.subscribe(id);
      }
    }catch(_){}
  }"""
if old not in s: raise SystemExit('connectBooking contract missing')
s=s.replace(old,new,1)

old="""    if(live!=null){
      tracking=DriverTracking.fromJson(live).keepLastLocation(tracking);
      notifyListeners();
      return;
    }
    final now=DateTime.now();
    if(_lastWordPressTracking!=null&&now.difference(_lastWordPressTracking!)<const Duration(seconds:12))return;
"""
new="""    if(live!=null){
      tracking=DriverTracking.fromJson(live).keepLastLocation(tracking);
      final liveStatus=live['status']?.toString();
      if(liveStatus!=null&&liveStatus.isNotEmpty&&activeBooking!=null&&liveStatus!=activeBooking!.status){
        unawaited(refreshBooking(id,silent:true));
      }
      notifyListeners();
      return;
    }
    final now=DateTime.now();
    if(_lastWordPressTracking!=null&&now.difference(_lastWordPressTracking!)<const Duration(seconds:4))return;
"""
if old not in s: raise SystemExit('realtime tracking block missing')
s=s.replace(old,new,1)

old="  Future<PassengerBooking> createBooking(VehicleQuote vehicle,{String paymentMethod='online'}) async {if(_api==null||lastQuoteRequest==null)throw const ApiException('Request a fare first.');final body=<String,Object?>{...lastQuoteRequest!,'vehicle_id':vehicle.id,'payment_method':paymentMethod,'terms_accept':true};busy=true;notifyListeners();try{final r=await _api!.createBooking(body);final b=PassengerBooking.fromJson(Map<String,dynamic>.from(r['booking'] as Map));bookings.insert(0,b);activeBooking=b;await _connectBooking(b.id);return b;}finally{busy=false;notifyListeners();}}"
new="""  Future<PassengerBooking> createBooking(VehicleQuote vehicle,{String paymentMethod='online'}) async {
    if(_api==null||lastQuoteRequest==null)throw const ApiException('Request a fare first.');
    final body=<String,Object?>{...lastQuoteRequest!,'vehicle_id':vehicle.id,'payment_method':paymentMethod,'terms_accept':true};
    busy=true;notifyListeners();
    try{
      final r=await _api!.createBooking(body).timeout(const Duration(seconds:15));
      final raw=r['booking'];
      if(raw is! Map)throw const ApiException('Invalid booking response.');
      final b=PassengerBooking.fromJson(Map<String,dynamic>.from(raw));
      bookings.removeWhere((x)=>x.id==b.id);
      bookings.insert(0,b);
      activeBooking=b;
      tracking=null;
      notifyListeners();
      unawaited(_connectBooking(b.id));
      unawaited(refreshBooking(b.id,silent:true));
      return b;
    }finally{
      busy=false;notifyListeners();
    }
  }"""
if old not in s: raise SystemExit('createBooking contract missing')
s=s.replace(old,new,1)
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.6+17'],
  'lib/config/app_config.dart':["version = '0.5.6'"],
  'lib/screens/home_screen.dart':['Passenger v0.5.6','size: 38','PremiumCarMarker'],
  'lib/screens/quote_screen.dart':['size:38','PremiumCarMarker(headingDegrees:0,size:42'],
  'lib/screens/trip_screen.dart':['premium_car_marker.dart','heading: tracking?.heading ?? 0','size: 40'],
  'lib/state/passenger_session.dart':['_bookingRefreshInFlight','Duration(seconds:1)','Duration(milliseconds:1500)','unawaited(_connectBooking(b.id))','Duration(seconds:4)'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
print('Passenger v0.5.6 small premium cars + ride sync self-heal applied')
