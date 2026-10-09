from pathlib import Path
import re

root=Path('driver')

def rep(rel,old,new,label):
    p=root/rel;s=p.read_text()
    if old not in s: raise SystemExit(f'{label}: marker missing in {rel}')
    p.write_text(s.replace(old,new,1))

rep('pubspec.yaml','version: 0.6.4+19','version: 0.6.5+20','pubspec version')
rep('lib/config/app_config.dart',"static const String version = '0.6.4';","static const String version = '0.6.5';",'app version')

# Android caches notification-channel sound configuration. Move chat to a fresh channel
# while leaving ride/job offer channels unchanged.
p=root/'lib/services/offer_notification_service.dart';s=p.read_text()
if "'gmp_driver_messages_v4'" not in s: raise SystemExit('driver chat channel marker missing')
s=s.replace("'gmp_driver_messages_v4'","'gmp_driver_messages_v5'",1)
p.write_text(s)

# Global REST fallback for passenger messages. Realtime/FCM still handle the fast path,
# but every active job is also checked periodically so repeated messages cannot disappear.
p=root/'lib/state/app_session.dart';s=p.read_text()
marker='  DateTime? _lastChatAlertAt;\n'
if marker not in s: raise SystemExit('driver chat alert state marker missing')
if '_globalChatPollInFlight' not in s:
    s=s.replace(marker,marker+"  bool _globalChatPollInFlight = false;\n  final Map<int,int> _globalChatCursor = <int,int>{};\n",1)
s=s.replace("if (messageId > 0) _lastChatAlertMessageId = messageId;",
            "if (messageId > 0) {_lastChatAlertMessageId = messageId;final old=_globalChatCursor[resolvedBooking]??0;if(messageId>old)_globalChatCursor[resolvedBooking]=messageId;}",1)
insert='  void clearChatAlert(int bookingId)'
idx=s.find(insert)
if idx<0: raise SystemExit('driver clearChatAlert marker missing')
method=r'''  Future<void> pollIncomingChatGlobal() async {
    final job=currentJob;
    if(job==null||_globalChatPollInFlight)return;
    final id=job.id;
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
        if(m.id<=cursor||m.senderRole=='driver')continue;
        notifyIncomingChatFromPoll(bookingId:id,messageId:m.id,senderName:m.senderName,preview:m.message);
      }
    }catch(_){
      // Retry silently on the next tick after temporary DNS/network loss.
    }finally{
      _globalChatPollInFlight=false;
    }
  }

'''
s=s[:idx]+method+s[idx:]
p.write_text(s)

# Poll from the persistent driver home route; pushed job/chat screens leave this state alive.
p=root/'lib/screens/driver_home_screen.dart';s=p.read_text()
if "import 'dart:async';" not in s:
    s="import 'dart:async';\n"+s
if 'Timer? _chatAlertPollTimer;' not in s:
    m=re.search(r'^(\s*)int _lastChatAlertSequence\s*=\s*0;\s*$',s,re.M)
    if not m: raise SystemExit('driver home chat sequence marker missing')
    s=s[:m.end()]+"\n"+m.group(1)+"Timer? _chatAlertPollTimer;"+s[m.end():]
if '_chatAlertPollTimer=Timer.periodic' not in s:
    pos=s.find('    super.initState();')
    if pos<0: raise SystemExit('driver home init marker missing')
    end=s.find('\n',pos)+1
    s=s[:end]+"    _chatAlertPollTimer=Timer.periodic(const Duration(seconds:3),(_)=>unawaited(widget.session.pollIncomingChatGlobal()));\n    WidgetsBinding.instance.addPostFrameCallback((_){unawaited(widget.session.pollIncomingChatGlobal());});\n"+s[end:]
if '_chatAlertPollTimer?.cancel();' not in s:
    pos=s.find('    super.dispose();')
    if pos<0: raise SystemExit('driver home dispose marker missing')
    s=s[:pos]+"    _chatAlertPollTimer?.cancel();\n"+s[pos:]
p.write_text(s)

checks={
 'pubspec.yaml':['version: 0.6.5+20'],
 'lib/config/app_config.dart':["version = '0.6.5'"],
 'lib/services/offer_notification_service.dart':['gmp_driver_messages_v5'],
 'lib/state/app_session.dart':['pollIncomingChatGlobal','_globalChatCursor'],
 'lib/screens/driver_home_screen.dart':['_chatAlertPollTimer','pollIncomingChatGlobal'],
}
for rel,needles in checks.items():
    text=(root/rel).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {rel}')
print('Applied Driver v0.6.5 persistent chat notifications fix.')
