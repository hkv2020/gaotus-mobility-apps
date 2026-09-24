from pathlib import Path

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
    s=s.replace('  flutter_local_notifications: ^19.5.0\n','  flutter_local_notifications: ^19.5.0\n  audioplayers: ^6.5.0\n',1)
p.write_text(s)

# Direct foreground playback + a new Android channel ID (channel sound settings are immutable).
p=root/'lib/services/offer_notification_service.dart'
s=p.read_text()
if "package:audioplayers/audioplayers.dart" not in s:
    s=s.replace("import 'package:flutter_local_notifications/flutter_local_notifications.dart';\n","import 'package:flutter_local_notifications/flutter_local_notifications.dart';\nimport 'package:audioplayers/audioplayers.dart';\n",1)
if 'final AudioPlayer _audio = AudioPlayer();' not in s:
    s=s.replace('  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();\n','  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();\n  final AudioPlayer _audio = AudioPlayer();\n',1)
if 'Future<void> _playAlert()' not in s:
    marker='  Future<void> showOffer({required int id, required String pickup, required String dropoff, required double total}) async {\n'
    method="""  Future<void> _playAlert() async {
    try {
      await _audio.stop();
      await _audio.play(AssetSource('audio/gaotus_alert.mp3'), volume: 1.0);
    } catch (_) {}
  }

"""
    if marker not in s: raise SystemExit('show offer marker missing')
    s=s.replace(marker,method+marker,1)
s=s.replace('    if (!initialized) return;\n','    await _playAlert();\n    if (!initialized) return;\n',1)
s=s.replace("'gmp_trip_requests',","'gmp_trip_requests_v3',",1)
p.write_text(s)

# Keep currently-live requests through short snapshot gaps so a dismissed popup remains in Jobs.
p=root/'lib/state/app_session.dart'
s=p.read_text()
old="""    if (raw is! List) {
      offers = <JobOffer>[];
      return;
    }
    final next = raw
        .whereType<Map>()
        .map((item) => JobOffer.fromJson(Map<String, dynamic>.from(item)))
        .where((offer) => !offer.expired && offer.status == 'offered')
        .toList();
    offers = next;
"""
new="""    if (raw is! List) return;
    final next = raw
        .whereType<Map>()
        .map((item) => JobOffer.fromJson(Map<String, dynamic>.from(item)))
        .where((offer) => !offer.expired && offer.status == 'offered')
        .toList();
    if(currentJob!=null){
      offers=<JobOffer>[];
    }else if(next.isNotEmpty){
      final byId=<int,JobOffer>{for(final offer in offers.where((item)=>!item.expired)) offer.id:offer};
      for(final offer in next)byId[offer.id]=offer;
      offers=byId.values.where((item)=>!item.expired).toList()
        ..sort((a,b)=>a.expiresAt.compareTo(b.expiresAt));
    }else{
      offers=offers.where((item)=>!item.expired).toList();
    }
"""
if old not in s: raise SystemExit('apply offers replacement marker missing')
s=s.replace(old,new,1)
p.write_text(s)

# Dedicated Nearby Jobs board.
(root/'lib/screens/nearby_jobs_screen.dart').write_text(r'''import 'dart:async';

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
    _refresh=Timer.periodic(const Duration(seconds:2),(_)=>unawaited(widget.session.refreshOperationalState(silent:true)));
    WidgetsBinding.instance.addPostFrameCallback((_)=>unawaited(widget.session.refreshOperationalState(silent:true)));
  }

  @override
  void dispose() {
    _refresh?.cancel();
    super.dispose();
  }

  Future<void> _accept(JobOffer offer) async {
    try {
      await widget.session.acceptOffer(offer);
      if(!mounted)return;
      await Navigator.of(context).push(MaterialPageRoute<void>(builder:(_)=>JobScreen(session:widget.session)));
    } catch (_) {
      if(!mounted)return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(widget.session.errorMessage??'Could not accept trip.')));
    }
  }

  Future<void> _decline(JobOffer offer) async {
    try {
      await widget.session.declineOffer(offer);
    } catch (_) {
      if(!mounted)return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(widget.session.errorMessage??'Could not decline trip.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation:widget.session,
      builder:(context,_) {
        final active=widget.session.offers.where((item)=>!item.expired).toList();
        final current=widget.session.currentJob;
        return Scaffold(
          appBar:AppBar(
            automaticallyImplyLeading:false,
            title:const Text('Nearby jobs',style:TextStyle(fontWeight:FontWeight.w900)),
            actions:<Widget>[
              IconButton(
                tooltip:'Refresh jobs',
                onPressed:()=>widget.session.refreshOperationalState(),
                icon:const Icon(Icons.refresh_rounded),
              ),
            ],
          ),
          body:RefreshIndicator(
            onRefresh:()=>widget.session.refreshOperationalState(),
            child:ListView(
              physics:const AlwaysScrollableScrollPhysics(),
              padding:const EdgeInsets.fromLTRB(18,8,18,28),
              children:<Widget>[
                if(current!=null)...<Widget>[
                  Container(
                    padding:const EdgeInsets.all(16),
                    decoration:BoxDecoration(color:const Color(0xFF111111),borderRadius:BorderRadius.circular(22)),
                    child:Row(children:<Widget>[
                      const CircleAvatar(backgroundColor:Colors.white,child:Icon(Icons.route_rounded,color:Colors.black)),
                      const SizedBox(width:12),
                      Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:<Widget>[
                        const Text('Active trip',style:TextStyle(color:Colors.white,fontWeight:FontWeight.w900,fontSize:17)),
                        const SizedBox(height:3),
                        Text(current.pickup,maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(color:Color(0xFFCCCCCC))),
                      ])),
                      FilledButton(
                        style:FilledButton.styleFrom(backgroundColor:Colors.white,foregroundColor:Colors.black),
                        onPressed:()=>Navigator.of(context).push(MaterialPageRoute<void>(builder:(_)=>JobScreen(session:widget.session))),
                        child:const Text('Open'),
                      ),
                    ]),
                  ),
                  const SizedBox(height:20),
                ],
                Row(children:<Widget>[
                  Expanded(child:Text('Trip requests',style:Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight:FontWeight.w900))),
                  if(active.isNotEmpty)Badge.count(count:active.length),
                ]),
                const SizedBox(height:6),
                Text(
                  active.isEmpty?'New nearby requests will stay available here while their offer window is open.':'If you close the pop-up, the request stays here until it expires or you respond.',
                  style:const TextStyle(color:Color(0xFF666666)),
                ),
                const SizedBox(height:16),
                if(active.isEmpty)
                  Container(
                    padding:const EdgeInsets.symmetric(vertical:46,horizontal:24),
                    decoration:BoxDecoration(color:const Color(0xFFF4F4F4),borderRadius:BorderRadius.circular(24)),
                    child:const Column(children:<Widget>[
                      Icon(Icons.radar_rounded,size:42),
                      SizedBox(height:12),
                      Text('No nearby requests right now',style:TextStyle(fontSize:18,fontWeight:FontWeight.w900)),
                      SizedBox(height:5),
                      Text('Stay online. New jobs appear here automatically.',textAlign:TextAlign.center,style:TextStyle(color:Color(0xFF666666))),
                    ]),
                  )
                else
                  ...active.map((offer)=>Padding(
                    padding:const EdgeInsets.only(bottom:14),
                    child:OfferCard(
                      offer:offer,
                      onAccept:()=>_accept(offer),
                      onDecline:()=>_decline(offer),
                    ),
                  )),
              ],
            ),
          ),
        );
      },
    );
  }
}
''')

# Add Jobs as a first-class bottom-navigation area with badge.
p=root/'lib/screens/driver_home_screen.dart'
s=p.read_text()
if "import 'nearby_jobs_screen.dart';" not in s:
    s=s.replace("import 'job_screen.dart';\n","import 'job_screen.dart';\nimport 'nearby_jobs_screen.dart';\n",1)
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
      NearbyJobsScreen(session: widget.session),
      EarningsScreen(session: widget.session, embedded: true),
      DriverMenuScreen(session: widget.session),
    ];
"""
if old not in s: raise SystemExit('driver pages marker missing')
s=s.replace(old,new,1)
old_nav="""        destinations: const <NavigationDestination>[
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.account_balance_wallet_outlined), selectedIcon: Icon(Icons.account_balance_wallet_rounded), label: 'Earnings'),
          NavigationDestination(icon: Icon(Icons.menu_rounded), selectedIcon: Icon(Icons.menu_open_rounded), label: 'Menu'),
        ],
"""
new_nav="""        destinations: <NavigationDestination>[
          const NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'Home'),
          NavigationDestination(
            icon: widget.session.offers.isEmpty
                ? const Icon(Icons.work_outline_rounded)
                : Badge.count(count:widget.session.offers.length,child:const Icon(Icons.work_outline_rounded)),
            selectedIcon: const Icon(Icons.work_rounded),
            label: 'Jobs',
          ),
          const NavigationDestination(icon: Icon(Icons.account_balance_wallet_outlined), selectedIcon: Icon(Icons.account_balance_wallet_rounded), label: 'Earnings'),
          const NavigationDestination(icon: Icon(Icons.menu_rounded), selectedIcon: Icon(Icons.menu_open_rounded), label: 'Menu'),
        ],
"""
if old_nav not in s: raise SystemExit('driver nav marker missing')
s=s.replace(old_nav,new_nav,1)
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.7+12','audioplayers:'],
  'lib/config/app_config.dart':["version = '0.5.7'"],
  'lib/services/offer_notification_service.dart':['AssetSource','gmp_trip_requests_v3'],
  'lib/state/app_session.dart':['byId=<int,JobOffer>','offers=offers.where((item)=>!item.expired)'],
  'lib/screens/nearby_jobs_screen.dart':['Nearby jobs','Trip requests','Timer.periodic(const Duration(seconds:2)'],
  'lib/screens/driver_home_screen.dart':['NearbyJobsScreen','label: \'Jobs\'','Badge.count'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
print('Driver v0.5.7 jobs board + durable offers + direct sound patch applied')
