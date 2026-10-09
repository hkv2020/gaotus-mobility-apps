from pathlib import Path

root=Path('driver')

def replace_once(rel, old, new, label):
    p=root/rel
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label}: marker missing in {rel}')
    p.write_text(s.replace(old,new,1))

replace_once('pubspec.yaml','version: 0.6.3+18','version: 0.6.4+19','pubspec version')
replace_once('lib/config/app_config.dart',"static const String version = '0.6.3';","static const String version = '0.6.4';",'app version')

# Localization for graceful transient network handling.
p=root/'lib/core/localization.dart'
s=p.read_text()
needle='    "You have a new job message.": "Ai primit un mesaj nou despre cursă.",\n'
if needle in s and 'Connection interrupted. Retrying automatically…' not in s:
    s=s.replace(needle,needle+'    "Connection interrupted. Retrying automatically…": "Conexiunea a fost întreruptă. Reîncercăm automat…",\n    "Message could not be sent. Please try again.": "Mesajul nu a putut fi trimis. Încearcă din nou.",\n',1)
p.write_text(s)

# Session-level message-id/fingerprint dedupe plus poll fallback.
p=root/'lib/state/app_session.dart'
s=p.read_text()
state_marker='  int _lastChatAlertEventId = 0;\n'
if state_marker not in s:
    raise SystemExit('driver chat state marker missing')
if '_lastChatAlertMessageId' not in s:
    s=s.replace(state_marker,state_marker+"  int _lastChatAlertMessageId = 0;\n  String _lastChatAlertFingerprint = '';\n  DateTime? _lastChatAlertAt;\n",1)
start=s.find('  void _announceChatAlert({')
end=s.find('  void clearChatAlert',start)
if start<0 or end<0:
    raise SystemExit('driver announce chat markers missing')
new_alert=r'''  void _announceChatAlert({required int eventId, required int bookingId, required String preview, String title = '', int messageId = 0}) {
    if (eventId > 0 && eventId == _lastChatAlertEventId) return;
    if (messageId > 0 && messageId == _lastChatAlertMessageId) return;
    final cleanPreview=preview.trim();
    final resolvedBooking=bookingId > 0 ? bookingId : (currentJob?.id ?? 0);
    final fingerprint='$resolvedBooking|$cleanPreview';
    final now=DateTime.now();
    if(fingerprint==_lastChatAlertFingerprint&&_lastChatAlertAt!=null&&now.difference(_lastChatAlertAt!)<const Duration(seconds:10))return;
    if (eventId > 0) _lastChatAlertEventId = eventId;
    if (messageId > 0) _lastChatAlertMessageId = messageId;
    _lastChatAlertFingerprint=fingerprint;
    _lastChatAlertAt=now;
    chatAlertBookingId = resolvedBooking;
    chatAlertTitle = title.trim().isEmpty ? 'Message from passenger'.tr : title.trim();
    chatAlertPreview = cleanPreview.isEmpty ? 'You have a new job message.'.tr : cleanPreview;
    chatAlertSequence++;
    if (hapticsEnabled) HapticFeedback.heavyImpact();
    unawaited(_offerNotifications.showChatMessage(
      eventId: eventId > 0 ? eventId : messageId,
      bookingId: chatAlertBookingId,
      title: chatAlertTitle,
      preview: chatAlertPreview,
      playForegroundSound: chatSoundEnabled,
    ));
    notifyListeners();
  }

  void notifyIncomingChatFromPoll({required int bookingId, required int messageId, required String senderName, required String preview}) {
    final title=senderName.trim().isEmpty?'Message from passenger'.tr:'${'Message from passenger'.tr} · ${senderName.trim()}';
    _announceChatAlert(eventId:0,bookingId:bookingId,preview:preview,title:title,messageId:messageId);
  }

'''
s=s[:start]+new_alert+s[end:]
# Realtime message id if present.
old="""        _announceChatAlert(
          eventId: eventId,
          bookingId: intValue(event['booking_id'] ?? payload['booking_id']),
          title: senderName.isNotEmpty ? '${'Message from passenger'.tr} · $senderName' : 'Message from passenger'.tr,
          preview: (message['message'] ?? payload['message_text'] ?? '').toString(),
        );"""
new="""        _announceChatAlert(
          eventId: eventId,
          bookingId: intValue(event['booking_id'] ?? payload['booking_id']),
          title: senderName.isNotEmpty ? '${'Message from passenger'.tr} · $senderName' : 'Message from passenger'.tr,
          preview: (message['message'] ?? payload['message_text'] ?? '').toString(),
          messageId: intValue(message['id'] ?? payload['message_id']),
        );"""
if old not in s:
    raise SystemExit('driver realtime alert call marker missing')
s=s.replace(old,new,1)
old="""      _announceChatAlert(
        eventId: intValue(data['event_id']),
        bookingId: intValue(data['booking_id']),
        title: (data['notification_title'] ?? 'Message from passenger'.tr).toString(),
        preview: (data['notification_body'] ?? '').toString(),
      );"""
new="""      _announceChatAlert(
        eventId: intValue(data['event_id']),
        bookingId: intValue(data['booking_id']),
        title: (data['notification_title'] ?? 'Message from passenger'.tr).toString(),
        preview: (data['notification_body'] ?? '').toString(),
        messageId: intValue(data['message_id']),
      );"""
if old not in s:
    raise SystemExit('driver push alert call marker missing')
s=s.replace(old,new,1)
p.write_text(s)

# Replace compact chat screen with a resilient version. Polling failures are silent and
# incoming REST-discovered messages trigger the same sound/haptics as realtime/FCM.
p=root/'lib/screens/chat_screen.dart'
p.write_text(r'''import 'dart:async';

import 'package:flutter/material.dart';

import '../core/localization.dart';
import '../models/chat_message.dart';
import '../state/app_session.dart';

class DriverChatScreen extends StatefulWidget {
  const DriverChatScreen({super.key,required this.session,required this.bookingId});
  final AppSession session;
  final int bookingId;
  @override State<DriverChatScreen> createState()=>_DriverChatScreenState();
}

class _DriverChatScreenState extends State<DriverChatScreen>{
  final _controller=TextEditingController();
  final _scroll=ScrollController();
  final List<ChatMessage> _messages=<ChatMessage>[];
  Timer? _timer;
  bool _loading=true,_sending=false;
  int _lastId=0,_pollFailures=0;
  String? _error;

  @override
  void initState(){
    super.initState();
    widget.session.clearChatAlert(widget.bookingId);
    unawaited(_load(initial:true));
    _timer=Timer.periodic(const Duration(seconds:4),(_)=>unawaited(_load()));
  }

  Future<void> _load({bool initial=false})async{
    try{
      final rows=await widget.session.chatMessages(widget.bookingId,afterId:initial?0:_lastId);
      if(!mounted)return;
      for(final m in rows){
        final isNew=_messages.every((x)=>x.id!=m.id);
        if(isNew){
          _messages.add(m);
          if(!initial&&m.senderRole!='driver'){
            widget.session.notifyIncomingChatFromPoll(bookingId:widget.bookingId,messageId:m.id,senderName:m.senderName,preview:m.message);
          }
        }
        if(m.id>_lastId)_lastId=m.id;
      }
      _messages.sort((a,b)=>a.id.compareTo(b.id));
      _pollFailures=0;
      _error=null;
      if(rows.isNotEmpty)WidgetsBinding.instance.addPostFrameCallback((_)=>_toBottom());
    }catch(_){
      _pollFailures++;
      if(initial&&_messages.isEmpty&&_pollFailures>=2)_error='Connection interrupted. Retrying automatically…'.tr;
    }finally{
      if(mounted)setState(()=>_loading=false);
    }
  }

  Future<void> _send()async{
    final text=_controller.text.trim();
    if(text.isEmpty||_sending)return;
    setState(()=>_sending=true);
    try{
      final m=await widget.session.sendChat(widget.bookingId,text);
      _controller.clear();
      if(_messages.every((x)=>x.id!=m.id))_messages.add(m);
      if(m.id>_lastId)_lastId=m.id;
      _error=null;
      WidgetsBinding.instance.addPostFrameCallback((_)=>_toBottom());
    }catch(_){
      _error='Message could not be sent. Please try again.'.tr;
    }finally{
      if(mounted)setState(()=>_sending=false);
    }
  }

  void _toBottom(){if(_scroll.hasClients)_scroll.animateTo(_scroll.position.maxScrollExtent,duration:const Duration(milliseconds:220),curve:Curves.easeOut);}

  @override
  void dispose(){_timer?.cancel();_controller.dispose();_scroll.dispose();super.dispose();}

  @override
  Widget build(BuildContext context)=>Scaffold(
    backgroundColor:Colors.white,
    appBar:AppBar(title:Text('Passenger chat'.tr)),
    body:SafeArea(child:Column(children:<Widget>[
      Expanded(child:_loading&&_messages.isEmpty
        ?const Center(child:CircularProgressIndicator())
        :_messages.isEmpty
          ?Center(child:Text(_error??'No messages yet.'.tr))
          :ListView.builder(
            controller:_scroll,
            padding:const EdgeInsets.all(14),
            itemCount:_messages.length,
            itemBuilder:(context,i){
              final m=_messages[i];final mine=m.senderRole=='driver';
              return Align(
                alignment:mine?Alignment.centerRight:Alignment.centerLeft,
                child:Container(
                  margin:const EdgeInsets.symmetric(vertical:4),
                  padding:const EdgeInsets.symmetric(horizontal:14,vertical:10),
                  constraints:BoxConstraints(maxWidth:MediaQuery.sizeOf(context).width*.78),
                  decoration:BoxDecoration(color:mine?Colors.black:const Color(0xFFF0F0F0),borderRadius:BorderRadius.circular(18)),
                  child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:<Widget>[
                    Text(m.message,style:TextStyle(color:mine?Colors.white:Colors.black)),
                    if(m.senderName.isNotEmpty)Padding(padding:const EdgeInsets.only(top:4),child:Text(mine?'You':m.senderName,style:TextStyle(fontSize:11,color:mine?Colors.white70:const Color(0xFF666666)))),
                  ]),
                ),
              );
            },
          )),
      if(_error!=null&&_messages.isEmpty)Padding(padding:const EdgeInsets.symmetric(horizontal:12),child:Text(_error!,style:TextStyle(color:Theme.of(context).colorScheme.error,fontSize:12))),
      Padding(
        padding:const EdgeInsets.fromLTRB(10,8,10,10),
        child:Row(children:<Widget>[
          Expanded(child:TextField(controller:_controller,textInputAction:TextInputAction.send,onSubmitted:(_)=>_send(),decoration:InputDecoration(hintText:'Message passenger…'.tr))),
          const SizedBox(width:8),
          IconButton.filled(onPressed:_sending?null:_send,icon:_sending?const SizedBox(width:20,height:20,child:CircularProgressIndicator(strokeWidth:2,color:Colors.white)):const Icon(Icons.send_rounded)),
        ]),
      ),
    ])),
  );
}
''')

checks={
  'lib/state/app_session.dart':['_lastChatAlertMessageId','notifyIncomingChatFromPoll','messageId: intValue'],
  'lib/screens/chat_screen.dart':['notifyIncomingChatFromPoll','_pollFailures','Connection interrupted. Retrying automatically'],
  'lib/config/app_config.dart':["version = '0.6.4'"],
  'pubspec.yaml':['version: 0.6.4+19'],
}
for rel,needles in checks.items():
    text=(root/rel).read_text()
    for needle in needles:
        if needle not in text:raise SystemExit(f'missing {needle} in {rel}')
print('Applied Driver v0.6.4 chat reliability fix.')
