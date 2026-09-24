from pathlib import Path

root=Path('passenger')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.3+14','version: 0.5.4+15','version')
replace_one('lib/config/app_config.dart',"static const version = '0.5.3';","static const version = '0.5.4';",'app version')

p=root/'lib/state/passenger_session.dart'
s=p.read_text()
if 'bool _nearbyInFlight=false;' not in s:
    s=s.replace('  DateTime? _lastNearbyWordPress;\n','  bool _nearbyInFlight=false;\n',1)

start=s.index('  Future<void> refreshNearby(double lat,double lng,{double radiusKm=8,int limit=12}) async {')
end=s.index('\n  Future<List<ChatMessage>>',start)
new=r'''  Future<void> refreshNearby(double lat,double lng,{double radiusKm=8,int limit=12}) async {
    if(!authenticated||_api==null||_nearbyInFlight)return;
    _nearbyInFlight=true;
    try{
      final merged=<NearbyCar>[];
      final seen=<String>{};
      void addCars(Object? raw){
        if(raw is! List)return;
        for(final item in raw.whereType<Map>()){
          final car=NearbyCar.fromJson(Map<String,dynamic>.from(item));
          if(!car.valid)continue;
          final key='${car.lat.toStringAsFixed(5)}:${car.lng.toStringAsFixed(5)}';
          if(seen.add(key))merged.add(car);
          if(merged.length>=limit)break;
        }
      }

      final liveFuture=(realtimeUrl!=null&&realtimeUrl!.isNotEmpty)
          ? _realtime.pollNearby(lat,lng,radiusKm:radiusKm,limit:limit)
          : Future<Map<String,dynamic>?>.value(null);
      final wpFuture=_api!.nearbyDrivers(lat,lng,radiusKm:radiusKm,limit:limit)
          .timeout(const Duration(seconds:4))
          .then<Map<String,dynamic>?>((value)=>value)
          .catchError((_)=><String,dynamic>{});
      final sources=await Future.wait<Map<String,dynamic>?>(<Future<Map<String,dynamic>?>>[liveFuture,wpFuture]);
      addCars(sources[0]?['cars']);
      addCars(sources[1]?['cars']);
      nearbyCars=merged.take(limit).toList();
      notifyListeners();
    }finally{
      _nearbyInFlight=false;
    }
  }
'''
s=s[:start]+new+s[end:]
p.write_text(s)

p=root/'lib/screens/home_screen.dart'
s=p.read_text().replace('Passenger v0.5.3','Passenger v0.5.4')
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.4+15'],
  'lib/config/app_config.dart':["version = '0.5.4'"],
  'lib/state/passenger_session.dart':['_nearbyInFlight','Duration(seconds:3)','nearbyDrivers','pollNearby'],
  'lib/screens/home_screen.dart':['Passenger v0.5.4'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
print('Passenger v0.5.4 nearby merge patch applied')
