from pathlib import Path
import re

root=Path('passenger')

def rep(rel,old,new,label):
    p=root/rel;s=p.read_text()
    if old not in s: raise SystemExit(f'{label}: marker missing in {rel}')
    p.write_text(s.replace(old,new,1))

rep('pubspec.yaml','version: 0.6.3+24','version: 0.6.4+25','pubspec version')
rep('lib/config/app_config.dart',"static const version = '0.6.3';","static const version = '0.6.4';",'app version')

# Android notification channels are immutable after creation. Use a fresh chat channel
# and a unique notification id per message so every new message can alert again.
p=root/'lib/services/passenger_notification_service.dart';s=p.read_text()
s=s.replace("'gmp_passenger_messages_v3'","'gmp_passenger_messages_v4'",1)
if 'int messageId = 0' not in s:
    s=re.sub(r"Future<void> showMessage\(\{\s*required int bookingId,\s*required String title,\s*required String body,\s*\}\) async \{",
             "Future<void> showMessage({\n    required int bookingId,\n    required String title,\n    required String body,\n    int messageId = 0,\n  }) async {",s,count=1)
s=s.replace('500000 + (bookingId % 499999),','500000 + ((messageId > 0 ? messageId : DateTime.now().millisecondsSinceEpoch) % 499999),',1)
p.write_text(s)

# Add a global REST fallback. Realtime/FCM remain accelerators, but they are no longer
# the only way to discover an incoming message while the user is outside Chat.
p=root/'lib/state/passenger_session.dart';s=p.read_text()
marker='  DateTime? _lastChatAlertAt;\n'
if marker not in s: raise SystemExit('chat alert state marker missing')
if '_globalChatPollInFlight' not in s:
    s=s.replace(marker,marker+"  bool _globalChatPollInFlight=false;\n  final Map<int,int> _globalChatCursor=<int,int>{};\n",1)
s=s.replace("if(messageId>0)_lastChatAlertMessageId=messageId;",
            "if(messageId>0){_lastChatAlertMessageId=messageId;final old=_globalChatCursor[bookingId]??0;if(messageId>old)_globalChatCursor[bookingId]=messageId;}",1)
s=s.replace("_notifications.showMessage(bookingId:chatAlertBookingId,title:chatAlertTitle,body:chatAlertPreview)",
            "_notifications.showMessage(bookingId:chatAlertBookingId,title:chatAlertTitle,body:chatAlertPreview,messageId:messageId)",1)
insert='  void clearChatAlert(int bookingId){\n'
if insert not in s: raise SystemExit('clearChatAlert marker missing')
method=r'''  Future<void> pollIncomingChatGlobal() async {
    final booking=activeBooking;
    if(booking==null||_globalChatPollInFlight)return;
    final id=booking.id;
    _globalChatPollInFlight=true;
    try{
      final known=_globalChatCursor.containsKey(id);
      final cursor=_globalChatCursor[id]??_lastChatAlertMessageId;
      final rows=await chatMessages(id,afterId:cursor);
      if(rows.isEmpty)return;
      rows.sort((a,b)=>a.id.compareTo(b.id));
      var maxId=cursor;
      for(final m in rows){if(m.id>maxId)maxId=m.id;}
      _globalChatCursor[id]=maxId;
      if(!known&&cursor==0)return;
      for(final m in rows){
        if(m.id<=cursor||m.senderRole=='customer')continue;
        notifyIncomingChatFromPoll(bookingId:id,messageId:m.id,senderName:m.senderName,preview:m.message);
      }
    }catch(_){
      // Silent fallback: transient mobile network/DNS misses are retried on next tick.
    }finally{
      _globalChatPollInFlight=false;
    }
  }

'''
s=s.replace(insert,method+insert,1)
p.write_text(s)

# Keep a lightweight chat fallback alive from the app home route. Pushed screens do not
# dispose HomeScreen, so this also covers quote/trip/delivery screens in foreground.
p=root/'lib/screens/home_screen.dart';s=p.read_text()
if 'Timer? _chatAlertPollTimer;' not in s:
    s=s.replace('  int _lastChatAlertSequence=0;\n','  int _lastChatAlertSequence=0;\n  Timer? _chatAlertPollTimer;\n',1)
init='    super.initState();\n'
if init not in s: raise SystemExit('home init marker missing')
if '_chatAlertPollTimer=Timer.periodic' not in s:
    s=s.replace(init,init+"    _chatAlertPollTimer=Timer.periodic(const Duration(seconds:3),(_)=>unawaited(widget.session.pollIncomingChatGlobal()));\n    WidgetsBinding.instance.addPostFrameCallback((_){unawaited(widget.session.pollIncomingChatGlobal());});\n",1)
if '_chatAlertPollTimer?.cancel();' not in s:
    s=s.replace('    nearbyTimer?.cancel();\n','    nearbyTimer?.cancel();\n    _chatAlertPollTimer?.cancel();\n',1)
p.write_text(s)

checks={
 'pubspec.yaml':['version: 0.6.4+25'],
 'lib/config/app_config.dart':["version = '0.6.4'"],
 'lib/services/passenger_notification_service.dart':['gmp_passenger_messages_v4','int messageId = 0','DateTime.now().millisecondsSinceEpoch'],
 'lib/state/passenger_session.dart':['pollIncomingChatGlobal','_globalChatCursor','messageId:messageId'],
 'lib/screens/home_screen.dart':['_chatAlertPollTimer','pollIncomingChatGlobal'],
}
for rel,needles in checks.items():
    text=(root/rel).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {rel}')
print('Applied Passenger v0.6.4 persistent chat notifications fix.')
