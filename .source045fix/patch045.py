from pathlib import Path

# Version markers.
p = Path('passenger/pubspec.yaml')
x = p.read_text()
if 'version: 0.4.3+7' not in x:
    raise SystemExit('pubspec v0.4.3 contract missing')
p.write_text(x.replace('version: 0.4.3+7', 'version: 0.4.5+9'))

p = Path('passenger/lib/config/app_config.dart')
x = p.read_text()
if "static const version = '0.4.3';" not in x:
    raise SystemExit('app config v0.4.3 contract missing')
p.write_text(x.replace("static const version = '0.4.3';", "static const version = '0.4.5';"))

# Start Flutter UI before network/session restoration so a restore error can never trap the app on native splash.
p = Path('passenger/lib/main.dart')
x = p.read_text()
if "import 'dart:async';" not in x:
    x = x.replace("import 'package:flutter/material.dart';", "import 'dart:async';\nimport 'package:flutter/material.dart';", 1)
old = "  final session = PassengerSession();\n  await session.initialize();\n  runApp(PassengerApp(session: session));"
new = "  final session = PassengerSession();\n  runApp(PassengerApp(session: session));\n  unawaited(session.initialize());"
if old not in x:
    raise SystemExit('main startup contract missing')
p.write_text(x.replace(old, new, 1))

# Harden session restoration and move optional realtime/push startup after UI authentication state is known.
p = Path('passenger/lib/state/passenger_session.dart')
x = p.read_text()
old = '''  Future<void> initialize() async {
    _realtime.onConnection=(v){realtimeConnected=v;notifyListeners();};
    _realtime.onEvent=(e){final type=e['type']?.toString();if(type=='driver.location'){tracking=DriverTracking.fromJson(<String,dynamic>{'tracking':true,'has_location':true,'signal':'live','status':activeBooking?.status??'assigned',...e}).keepLastLocation(tracking);notifyListeners();}else if(activeBooking!=null){unawaited(refreshBooking(activeBooking!.id,silent:true));}};
    _push.onToken=(v){if(authenticated)unawaited(_registerPush());};
    _push.onMessage=(d){unawaited(refreshBookings(silent:true));if(activeBooking!=null)unawaited(refreshBooking(activeBooking!.id,silent:true));};
    await _push.initialize();
    serverUrl=await _store.readServer() ?? serverUrl;
    token=await _store.readToken();
    realtimeUrl=await _store.readRealtime();
    if(serverUrl.isNotEmpty&&token!=null){_api=ApiClient(siteUrl:serverUrl,token:token);try{await _validateAndLoad();authenticated=true;await _discoverRealtime();await _registerPush();_startPoll();}on ApiException catch(e){if(e.statusCode==401||e.statusCode==403)await _clear();else errorMessage=e.message;}}
    booting=false;notifyListeners();
  }
'''
new = '''  Future<void> initialize() async {
    _realtime.onConnection=(v){realtimeConnected=v;notifyListeners();};
    _realtime.onEvent=(e){final type=e['type']?.toString();if(type=='driver.location'){tracking=DriverTracking.fromJson(<String,dynamic>{'tracking':true,'has_location':true,'signal':'live','status':activeBooking?.status??'assigned',...e}).keepLastLocation(tracking);notifyListeners();}else if(activeBooking!=null){unawaited(refreshBooking(activeBooking!.id,silent:true));}};
    _push.onToken=(v){if(authenticated)unawaited(_registerPush());};
    _push.onMessage=(d){unawaited(refreshBookings(silent:true));if(activeBooking!=null)unawaited(refreshBooking(activeBooking!.id,silent:true));};
    try {
      try { await _push.initialize().timeout(const Duration(seconds:8)); } catch (_) {}
      serverUrl=await _store.readServer().timeout(const Duration(seconds:5)) ?? serverUrl;
      token=await _store.readToken().timeout(const Duration(seconds:5));
      realtimeUrl=await _store.readRealtime().timeout(const Duration(seconds:5));
      if(serverUrl.isNotEmpty&&token!=null&&token!.isNotEmpty){
        _api=ApiClient(siteUrl:serverUrl,token:token);
        try {
          await _validateAndLoad().timeout(const Duration(seconds:30));
          authenticated=true;
          unawaited(_finishAuthenticatedBoot());
        } on ApiException catch(e) {
          if(e.statusCode==401||e.statusCode==403){await _clear();errorMessage='Your saved session expired. Please sign in again.';}
          else {errorMessage=e.message;authenticated=false;}
        } catch(e) {
          errorMessage='Could not restore the saved session: $e';
          authenticated=false;
        }
      }
    } catch(e) {
      errorMessage='Startup recovery: $e';
      authenticated=false;
    } finally {
      booting=false;
      notifyListeners();
    }
  }

  Future<void> _finishAuthenticatedBoot() async {
    try { await _discoverRealtime().timeout(const Duration(seconds:8)); } catch (_) {}
    try { await _registerPush().timeout(const Duration(seconds:8)); } catch (_) {}
    _startPoll();
    final booking=activeBooking;
    if(booking!=null){try{await _connectBooking(booking.id).timeout(const Duration(seconds:10));}catch(_){}}
  }
'''
if old not in x:
    raise SystemExit('initialize contract missing')
x = x.replace(old, new, 1)

old = "  Future<void> _validateAndLoad() async {final api=_api!;final m=await api.me();identity=m['user'] is Map?Map<String,dynamic>.from(m['user'] as Map):null;await refreshBookings(silent:true);}"
new = "  Future<void> _validateAndLoad() async {final api=_api!;final m=await api.me();identity=m['user'] is Map?Map<String,dynamic>.from(m['user'] as Map):null;await refreshBookings(silent:true,connectRealtime:false,propagateErrors:true);}"
if old not in x:
    raise SystemExit('validate/load contract missing')
x = x.replace(old, new, 1)

old = "  Future<void> refreshBookings({bool silent=false}) async {if(_api==null)return;if(!silent){busy=true;notifyListeners();}try{final r=await _api!.bookings();final raw=r['bookings'];bookings=raw is List?raw.whereType<Map>().map((e)=>PassengerBooking.fromJson(Map<String,dynamic>.from(e))).toList():<PassengerBooking>[];activeBooking=bookings.cast<PassengerBooking?>().firstWhere((b)=>b?.active==true,orElse:()=>null);if(activeBooking!=null)await _connectBooking(activeBooking!.id);}on ApiException catch(e){if(e.statusCode==401||e.statusCode==403)await _clear();else errorMessage=e.message;}finally{busy=false;notifyListeners();}}"
new = "  Future<void> refreshBookings({bool silent=false,bool connectRealtime=true,bool propagateErrors=false}) async {if(_api==null)return;if(!silent){busy=true;notifyListeners();}try{final r=await _api!.bookings();final raw=r['bookings'];bookings=raw is List?raw.whereType<Map>().map((e)=>PassengerBooking.fromJson(Map<String,dynamic>.from(e))).toList():<PassengerBooking>[];activeBooking=bookings.cast<PassengerBooking?>().firstWhere((b)=>b?.active==true,orElse:()=>null);if(connectRealtime&&activeBooking!=null)await _connectBooking(activeBooking!.id);}on ApiException catch(e){if(e.statusCode==401||e.statusCode==403)await _clear();else errorMessage=e.message;if(propagateErrors)rethrow;}catch(e){errorMessage='$e';if(propagateErrors)rethrow;}finally{busy=false;notifyListeners();}}"
if old not in x:
    raise SystemExit('refreshBookings contract missing')
x = x.replace(old, new, 1)

x = x.replace("await _validateAndLoad();authenticated=true;await _discoverRealtime();await _registerPush();_startPoll();", "await _validateAndLoad();authenticated=true;unawaited(_finishAuthenticatedBoot());")
p.write_text(x)

# Show restore/startup errors on login instead of hiding them.
p = Path('passenger/lib/screens/auth_screen.dart')
x = p.read_text()
needle = "                  const SizedBox(height: 30),\n"
box = '''                  const SizedBox(height: 30),
                  if (session.errorMessage != null && session.errorMessage!.isNotEmpty) ...<Widget>[
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(color: const Color(0xFFFFF2F0), borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFFFC7C0))),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                        const Icon(Icons.warning_amber_rounded, color: Color(0xFFB42318)),
                        const SizedBox(width: 10),
                        Expanded(child: Text(session.errorMessage!, style: const TextStyle(color: Color(0xFF7A271A), fontWeight: FontWeight.w700, height: 1.35))),
                      ]),
                    ),
                    const SizedBox(height: 16),
                  ],
'''
if needle not in x:
    raise SystemExit('auth UI contract missing')
p.write_text(x.replace(needle, box, 1))

# Accept geocoding fallback rows from Platform 1.3.11 directly without a second Place Details request.
p = Path('passenger/lib/models/place_selection.dart')
x = p.read_text()
old = '''final class PlaceSuggestion {
  const PlaceSuggestion({required this.placeId, required this.text, required this.mainText, required this.secondaryText});
  final String placeId;
  final String text;
  final String mainText;
  final String secondaryText;
  factory PlaceSuggestion.fromJson(Map<String,dynamic> j)=>PlaceSuggestion(
    placeId:(j['place_id']??'').toString(), text:(j['text']??'').toString(),
    mainText:(j['main_text']??'').toString(), secondaryText:(j['secondary_text']??'').toString(),
  );
}
'''
new = '''final class PlaceSuggestion {
  const PlaceSuggestion({required this.placeId, required this.text, required this.mainText, required this.secondaryText, this.lat, this.lng});
  final String placeId;
  final String text;
  final String mainText;
  final String secondaryText;
  final double? lat;
  final double? lng;
  bool get hasCoordinates => lat != null && lng != null;
  factory PlaceSuggestion.fromJson(Map<String,dynamic> j)=>PlaceSuggestion(
    placeId:(j['place_id']??'').toString(), text:(j['text']??'').toString(),
    mainText:(j['main_text']??'').toString(), secondaryText:(j['secondary_text']??'').toString(),
    lat:(j['lat'] as num?)?.toDouble()??double.tryParse('${j['lat']}'),
    lng:(j['lng'] as num?)?.toDouble()??double.tryParse('${j['lng']}'),
  );
}
'''
if old not in x:
    raise SystemExit('PlaceSuggestion contract missing')
p.write_text(x.replace(old, new, 1))

p = Path('passenger/lib/screens/place_search_screen.dart')
x = p.read_text()
old = '''  Future<void> pick(PlaceSuggestion suggestion) async{
    setState(()=>loading=true);
    try{
      final place=await widget.session.placeDetails(suggestion.placeId,sessionToken:sessionToken);
      if(mounted)Navigator.pop(context,place);
    }catch(e){if(mounted)setState(()=>error='$e');}
    finally{if(mounted)setState(()=>loading=false);}
  }
'''
new = '''  Future<void> pick(PlaceSuggestion suggestion) async{
    if(suggestion.hasCoordinates){
      Navigator.pop(context,PlaceSelection(address:suggestion.text.isNotEmpty?suggestion.text:suggestion.mainText,lat:suggestion.lat!,lng:suggestion.lng!,placeId:suggestion.placeId,name:suggestion.mainText));
      return;
    }
    setState(()=>loading=true);
    try{
      final place=await widget.session.placeDetails(suggestion.placeId,sessionToken:sessionToken);
      if(mounted)Navigator.pop(context,place);
    }catch(e){if(mounted)setState(()=>error='$e');}
    finally{if(mounted)setState(()=>loading=false);}
  }
'''
if old not in x:
    raise SystemExit('place pick contract missing')
p.write_text(x.replace(old, new, 1))

# UI build marker.
p = Path('passenger/lib/screens/home_screen.dart')
x = p.read_text().replace('Passenger v0.4.3', 'Passenger v0.4.5').replace('Pickup pin + Places suggestions + ride map markers', 'Startup recovery + Google fallback + trip markers')
p.write_text(x)

# Static contracts.
assert 'version: 0.4.5+9' in Path('passenger/pubspec.yaml').read_text()
assert 'unawaited(session.initialize())' in Path('passenger/lib/main.dart').read_text()
assert 'Could not restore the saved session' in Path('passenger/lib/state/passenger_session.dart').read_text()
assert 'hasCoordinates' in Path('passenger/lib/models/place_selection.dart').read_text()
assert 'Passenger v0.4.5' in Path('passenger/lib/screens/home_screen.dart').read_text()
print('Passenger v0.4.5 startup recovery patch applied')
