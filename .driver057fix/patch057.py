from pathlib import Path
import shutil

root=Path('driver')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.6+11','version: 0.5.7+12','version')
replace_one('lib/config/app_config.dart',"static const String version = '0.5.6';","static const String version = '0.5.7';",'app version')

p=root/'pubspec.yaml'
s=p.read_text()
if 'audioplayers:' not in s:
    s=s.replace('  flutter_local_notifications: ^19.5.0\n','  flutter_local_notifications: ^19.5.0\n  audioplayers: ^6.1.0\n',1)
p.write_text(s)

shutil.copyfile('.driver057fix/offer_notification_service.dart',root/'lib/services/offer_notification_service.dart')
shutil.copyfile('.driver057fix/driver_requests_screen.dart',root/'lib/screens/driver_requests_screen.dart')

p=root/'lib/core/api_client.dart'
s=p.read_text()
old="""  Future<Map<String, dynamic>> offers({int limit = 20}) => _request(
        'POST',
        '/driver/offers',
        body: <String, Object?>{'status': 'offered', 'limit': limit},
      );
"""
new="""  Future<Map<String, dynamic>> offers({String status = 'offered', int limit = 20}) => _request(
        'POST',
        '/driver/offers',
        body: <String, Object?>{'status': status, 'limit': limit},
      );
"""
if old not in s: raise SystemExit('api offers marker missing')
s=s.replace(old,new,1)
p.write_text(s)

p=root/'lib/services/realtime_service.dart'
s=p.read_text()
if 'Timer? _watchdog;' not in s:
    s=s.replace('  Timer? _heartbeat;\n','  Timer? _heartbeat;\n  Timer? _watchdog;\n',1)
if 'DateTime? _lastMessage;' not in s:
    s=s.replace('  bool _shouldReconnect = false;\n','  bool _shouldReconnect = false;\n  DateTime? _lastMessage;\n',1)
s=s.replace('      _subscription = channel.stream.listen(\n','      _lastMessage = DateTime.now();\n      _subscription = channel.stream.listen(\n',1)
s=s.replace("      _heartbeat = Timer.periodic(const Duration(seconds: 20), (_) => send(<String, Object?>{'type': 'ping'}));","      _heartbeat = Timer.periodic(const Duration(seconds: 15), (_) => send(<String, Object?>{'type': 'ping'}));\n      _watchdog = Timer.periodic(const Duration(seconds: 10), (_) { final last=_lastMessage; if(last!=null&&DateTime.now().difference(last)>const Duration(seconds:35)) _handleDisconnect(); });",1)
s=s.replace("      final event = Map<String, dynamic>.from(decoded);\n      if (event['type'] == 'auth.ok')","      _lastMessage = DateTime.now();\n      final event = Map<String, dynamic>.from(decoded);\n      if (event['type'] == 'auth.ok' || event['type'] == 'pong')",1)
s=s.replace('    _heartbeat?.cancel();\n    _heartbeat = null;','    _heartbeat?.cancel();\n    _heartbeat = null;\n    _watchdog?.cancel();\n    _watchdog = null;',1)
s=s.replace('    _reconnectTimer = Timer(const Duration(seconds: 6), _open);','    _reconnectTimer = Timer(const Duration(seconds: 3), _open);',1)
s=s.replace('    _heartbeat?.cancel(); _heartbeat = null;','    _heartbeat?.cancel(); _heartbeat = null;\n    _watchdog?.cancel(); _watchdog = null;',1)
p.write_text(s)

p=root/'lib/state/app_session.dart'
s=p.read_text()
if 'List<JobOffer> recentOffers = <JobOffer>[];' not in s:
    s=s.replace('  List<JobOffer> offers = <JobOffer>[];\n','  List<JobOffer> offers = <JobOffer>[];\n  List<JobOffer> recentOffers = <JobOffer>[];\n',1)

old="""    _applyCurrentJob(<String,dynamic>{'job': data['job']});
    _applyOffers(<String,dynamic>{'offers': data['offers']});
  }
"""
new="""    _applyCurrentJob(<String,dynamic>{'job': data['job']});
    _applyOffers(<String,dynamic>{'offers': data['offers']});
    final history = data['offer_history'];
    if (history is List) _applyOfferHistory(<String,dynamic>{'offers': history});
  }
"""
if old not in s: raise SystemExit('snapshot marker missing')
s=s.replace(old,new,1)

s=s.replace("        api.offers(),\n      ]);\n      _applyDriverMe(results[0]);\n      _applyCurrentJob(results[1]);\n      _applyOffers(results[2]);","        api.offers(status: 'all', limit: 40),\n      ]);\n      _applyDriverMe(results[0]);\n      _applyCurrentJob(results[1]);\n      _applyOfferHistory(results[2]);\n      _applyOffers(results[2]);",1)
s=s.replace("        api.offers(),\n      ]);\n      _applyCurrentJob(results[0]);\n      _applyOffers(results[1]);","        api.offers(status: 'all', limit: 40),\n      ]);\n      _applyCurrentJob(results[0]);\n      _applyOfferHistory(results[1]);\n      _applyOffers(results[1]);",1)

old="""    final rawOffers = data['offers'];
    if (rawOffers is List) {
      offers = rawOffers
          .whereType<Map>()
          .map((item) => JobOffer.fromJson(Map<String, dynamic>.from(item)))
          .where((offer) => !offer.expired)
          .toList();
    }
"""
new="""    final rawOffers = data['offers'];
    if (rawOffers is List) _applyOffers(<String,dynamic>{'offers': rawOffers});
"""
if old not in s: raise SystemExit('driver me offers marker missing')
s=s.replace(old,new,1)

start=s.index('  void _applyOffers(Map<String, dynamic> data) {')
end=s.index('\n  Future<void> _announceOffer',start)
new_methods=r'''  void _applyOffers(Map<String, dynamic> data) {
    final raw=data['offers'];
    if(currentJob!=null){offers=<JobOffer>[];return;}
    final now=DateTime.now().toUtc();
    final byId=<int,JobOffer>{};
    for(final existing in offers){
      if(existing.status=='offered'&&existing.expiresAt.isAfter(now))byId[existing.id]=existing;
    }
    if(raw is List){
      for(final item in raw.whereType<Map>()){
        try{
          final offer=JobOffer.fromJson(Map<String,dynamic>.from(item));
          if(offer.status=='offered'&&!offer.expired)byId[offer.id]=offer;
        }catch(_){}
      }
    }
    offers=byId.values.toList()..sort((a,b)=>a.expiresAt.compareTo(b.expiresAt));
    _mergeOfferHistory(offers);
    for(final offer in offers){
      if(_seenOfferIds.add(offer.id))unawaited(_announceOffer(offer));
    }
  }

  void _applyOfferHistory(Map<String,dynamic> data){
    final raw=data['offers'];if(raw is! List)return;
    final parsed=<JobOffer>[];
    for(final item in raw.whereType<Map>()){
      try{parsed.add(JobOffer.fromJson(Map<String,dynamic>.from(item)));}catch(_){}
    }
    _mergeOfferHistory(parsed);
  }

  void _mergeOfferHistory(Iterable<JobOffer> incoming){
    final byId=<int,JobOffer>{for(final item in recentOffers)item.id:item};
    for(final item in incoming)byId[item.id]=item;
    recentOffers=byId.values.toList()..sort((a,b)=>b.expiresAt.compareTo(a.expiresAt));
    if(recentOffers.length>50)recentOffers=recentOffers.take(50).toList();
  }
'''
s=s[:start]+new_methods+s[end:]

s=s.replace('            if (index >= 0) offers[index] = offer; else offers.insert(0, offer);\n            if (_seenOfferIds.add(offer.id))','            if (index >= 0) offers[index] = offer; else offers.insert(0, offer);\n            _mergeOfferHistory(<JobOffer>[offer]);\n            if (_seenOfferIds.add(offer.id))',1)
s=s.replace('      offers = offers.where((item) => item.id != offer.id).toList();\n      if (driverState != null) {','      offers = offers.where((item) => item.id != offer.id).toList();\n      _mergeOfferHistory(<JobOffer>[offer]);\n      if (driverState != null) {',1)
s=s.replace('      await api.declineOffer(offer.id);\n      offers = offers.where((item) => item.id != offer.id).toList();','      await api.declineOffer(offer.id);\n      offers = offers.where((item) => item.id != offer.id).toList();\n      _mergeOfferHistory(<JobOffer>[offer]);',1)
s=s.replace('      _seenOfferIds.clear();\n      await _store.clearSession();','      _seenOfferIds.clear();\n      recentOffers=<JobOffer>[];\n      await _store.clearSession();',1)
if 'unawaited(_offerNotifications.dispose());' not in s:
    s=s.replace('    unawaited(_push.dispose());\n    super.dispose();','    unawaited(_push.dispose());\n    unawaited(_offerNotifications.dispose());\n    super.dispose();',1)
p.write_text(s)

p=root/'lib/screens/driver_home_screen.dart'
s=p.read_text()
if "import 'driver_requests_screen.dart';" not in s:
    s=s.replace("import 'earnings_screen.dart';\n","import 'earnings_screen.dart';\nimport 'driver_requests_screen.dart';\n",1)

old="""    final pages = <Widget>[
      _DriverMapHome(
        session: widget.session,
        openEarnings: () => setState(() => _tab = 1),
        openJob: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => JobScreen(session: widget.session))),
      ),
      EarningsScreen(session: widget.session, embedded: true),
      DriverMenuScreen(session: widget.session),
    ];
"""
new="""    final pages = <Widget>[
      _DriverMapHome(
        session: widget.session,
        openEarnings: () => setState(() => _tab = 2),
        openJob: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => JobScreen(session: widget.session))),
      ),
      DriverRequestsScreen(session: widget.session),
      EarningsScreen(session: widget.session, embedded: true),
      DriverMenuScreen(session: widget.session),
    ];
"""
if old not in s: raise SystemExit('pages marker missing')
s=s.replace(old,new,1)

old="""        destinations: const <NavigationDestination>[
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.account_balance_wallet_outlined), selectedIcon: Icon(Icons.account_balance_wallet_rounded), label: 'Earnings'),
          NavigationDestination(icon: Icon(Icons.menu_rounded), selectedIcon: Icon(Icons.menu_open_rounded), label: 'Menu'),
        ],
"""
new="""        destinations: <NavigationDestination>[
          const NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'Home'),
          NavigationDestination(
            icon: Badge(isLabelVisible: widget.session.offers.isNotEmpty, label: Text('${widget.session.offers.length}'), child: const Icon(Icons.radar_outlined)),
            selectedIcon: Badge(isLabelVisible: widget.session.offers.isNotEmpty, label: Text('${widget.session.offers.length}'), child: const Icon(Icons.radar_rounded)),
            label: 'Requests',
          ),
          const NavigationDestination(icon: Icon(Icons.account_balance_wallet_outlined), selectedIcon: Icon(Icons.account_balance_wallet_rounded), label: 'Earnings'),
          const NavigationDestination(icon: Icon(Icons.menu_rounded), selectedIcon: Icon(Icons.menu_open_rounded), label: 'Menu'),
        ],
"""
if old not in s: raise SystemExit('nav marker missing')
s=s.replace(old,new,1)
p.write_text(s)

checks={
 'pubspec.yaml':['version: 0.5.7+12','audioplayers: ^6.1.0'],
 'lib/config/app_config.dart':["version = '0.5.7'"],
 'lib/core/api_client.dart':["offers({String status = 'offered'"],
 'lib/state/app_session.dart':['recentOffers','offer_history','_mergeOfferHistory'],
 'lib/services/realtime_service.dart':['_watchdog','Duration(seconds:35)','Duration(seconds: 3)'],
 'lib/services/offer_notification_service.dart':['AudioPlayer','gmp_trip_requests_v3'],
 'lib/screens/driver_home_screen.dart':['DriverRequestsScreen','label: \'Requests\''],
 'lib/screens/driver_requests_screen.dart':['Nearby requests','Recent requests'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
print('Driver v0.5.7 persistent request inbox patch applied')
