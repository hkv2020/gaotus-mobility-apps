from pathlib import Path

root = Path('passenger')

def replace_once(rel, old, new, label):
    p = root / rel
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'{label}: marker missing in {rel}')
    p.write_text(s.replace(old, new, 1))

replace_once('pubspec.yaml', 'version: 0.6.2+23', 'version: 0.6.3+24', 'pubspec version')
replace_once('lib/config/app_config.dart', "static const version = '0.6.2';", "static const version = '0.6.3';", 'app version')

# Localized reliability messages.
p = root / 'lib/core/localization.dart'
s = p.read_text()
marker = '    "You have a new message.": "Ai primit un mesaj nou.",\n'
if marker in s and 'Connection interrupted. Retrying automatically…' not in s:
    s = s.replace(marker, marker + '    "Connection interrupted. Retrying automatically…": "Conexiunea a fost întreruptă. Reîncercăm automat…",\n    "Message could not be sent. Please try again.": "Mesajul nu a putut fi trimis. Încearcă din nou.",\n    "Pick-up updated": "Locul de preluare a fost actualizat",\n    "Fare recalculated. Confirm the new fare to continue.": "Tariful a fost recalculat. Confirmă noul tarif pentru a continua.",\n    "Confirm ride": "Confirmă cursa",\n    "Not now": "Nu acum",\n', 1)
p.write_text(s)

# Ride booking: confirm the pickup pin only once. If the pin moved, recalculate,
# preserve the chosen vehicle and ask only for fare consent — never reopen the pin screen.
p = root / 'lib/screens/quote_screen.dart'
s = p.read_text()
field_marker = "  Timer? nearbyTimer;\n"
if field_marker not in s:
    raise SystemExit('quote nearbyTimer marker missing')
if '_pickupConfirmed' not in s:
    s = s.replace(field_marker, field_marker + '  bool _pickupConfirmed=false;\n', 1)
start = s.find('  Future<void> book() async{')
end = s.find('  Future<void> _performBooking', start)
if start < 0 or end < 0:
    raise SystemExit('quote book function markers missing')
new_book = r'''  Future<void> book() async{
    final vehicle=selected;
    if(vehicle==null)return;

    // Once the pickup was confirmed for this quote, subsequent vehicle/payment
    // changes must not reopen the pin screen.
    if(_pickupConfirmed){
      await _performBooking(vehicle);
      return;
    }

    final j=currentQuote.journey;
    final original=_point(j['pickup_lat'],j['pickup_lng']);
    if(original==null){
      _pickupConfirmed=true;
      await _performBooking(vehicle);
      return;
    }

    final confirmed=await Navigator.of(context).push<PlaceSelection>(
      MaterialPageRoute(
        builder:(_)=>PickupConfirmScreen(
          session:widget.session,
          initial:original,
          initialAddress:(j['pickup']??'').toString(),
        ),
      ),
    );
    if(confirmed==null||!mounted)return;

    final moved=(confirmed.lat-original.latitude).abs()>0.00012||(confirmed.lng-original.longitude).abs()>0.00012;
    if(!moved){
      _pickupConfirmed=true;
      await _performBooking(vehicle);
      return;
    }

    final previous=widget.session.lastQuoteRequest;
    if(previous==null){
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Could not refresh the fare. Please request the ride again.')));
      return;
    }

    try{
      final request=<String,Object?>{
        ...previous,
        'pickup':confirmed.address,
        'pickup_lat':confirmed.lat,
        'pickup_lng':confirmed.lng,
      };
      final refreshed=await widget.session.quote(request);
      if(!mounted)return;

      VehicleQuote? same;
      for(final option in refreshed.vehicles){
        if(option.id==vehicle.id){same=option;break;}
      }
      final bookingVehicle=same??(refreshed.vehicles.isNotEmpty?refreshed.vehicles.first:null);
      setState((){
        currentQuote=refreshed;
        selected=bookingVehicle;
        _pickupConfirmed=true;
      });
      if(bookingVehicle==null)return;

      final continueRide=await showDialog<bool>(
        context:context,
        builder:(dialogContext)=>AlertDialog(
          title:Text('Pick-up updated'.tr),
          content:Text('${'Fare recalculated. Confirm the new fare to continue.'.tr}\n\n${bookingVehicle.title}: ${bookingVehicle.priceLabel}'),
          actions:<Widget>[
            TextButton(onPressed:()=>Navigator.pop(dialogContext,false),child:Text('Not now'.tr)),
            FilledButton(onPressed:()=>Navigator.pop(dialogContext,true),child:Text('Confirm ride'.tr)),
          ],
        ),
      );
      if(continueRide==true&&mounted){
        await _performBooking(bookingVehicle);
      }
    }catch(error){
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Connection interrupted. Retrying automatically…')));
    }
  }

'''
s = s[:start] + new_book + s[end:]
p.write_text(s)

# Session-level chat fallback dedupe. Polling can discover a message when realtime/FCM
# missed it; that path must produce the same audible notification exactly once.
p = root / 'lib/state/passenger_session.dart'
s = p.read_text()
state_marker = '  int _lastChatAlertEventId=0;\n'
if state_marker not in s:
    raise SystemExit('passenger chat alert state marker missing')
if '_lastChatAlertMessageId' not in s:
    s = s.replace(state_marker, state_marker + "  int _lastChatAlertMessageId=0;\n  String _lastChatAlertFingerprint='';\n  DateTime? _lastChatAlertAt;\n", 1)
start = s.find('  void _announceChatAlert({')
end = s.find('  void clearChatAlert', start)
if start < 0 or end < 0:
    raise SystemExit('passenger announce chat function markers missing')
new_alert = r'''  void _announceChatAlert({required int eventId,required int bookingId,required String title,required String preview,int messageId=0}){
    if(eventId>0&&eventId==_lastChatAlertEventId)return;
    if(messageId>0&&messageId==_lastChatAlertMessageId)return;
    final cleanPreview=preview.trim();
    final fingerprint='${bookingId>0?bookingId:(activeBooking?.id??0)}|$cleanPreview';
    final now=DateTime.now();
    if(fingerprint==_lastChatAlertFingerprint&&_lastChatAlertAt!=null&&now.difference(_lastChatAlertAt!)<const Duration(seconds:10))return;
    if(eventId>0)_lastChatAlertEventId=eventId;
    if(messageId>0)_lastChatAlertMessageId=messageId;
    _lastChatAlertFingerprint=fingerprint;
    _lastChatAlertAt=now;
    chatAlertBookingId=bookingId>0?bookingId:(activeBooking?.id??0);
    chatAlertTitle=title.trim().isEmpty?'Message from your driver'.tr:title.trim();
    chatAlertPreview=cleanPreview.isEmpty?'You have a new message.'.tr:cleanPreview;
    chatAlertSequence++;
    if(chatAlertBookingId>0)unawaited(_notifications.showMessage(bookingId:chatAlertBookingId,title:chatAlertTitle,body:chatAlertPreview));
    notifyListeners();
  }

  void notifyIncomingChatFromPoll({required int bookingId,required int messageId,required String senderName,required String preview}){
    final title=senderName.trim().isEmpty?'Message from your driver'.tr:'${'Message from your driver'.tr} · ${senderName.trim()}';
    _announceChatAlert(eventId:0,bookingId:bookingId,title:title,preview:preview,messageId:messageId);
  }

'''
s = s[:start] + new_alert + s[end:]
# Feed message ids into realtime/push dedupe when available.
s = s.replace("_announceChatAlert(eventId:int.tryParse((e['event_id']??0).toString())??0,bookingId:bookingId,title:title,preview:preview);",
              "_announceChatAlert(eventId:int.tryParse((e['event_id']??0).toString())??0,bookingId:bookingId,title:title,preview:preview,messageId:int.tryParse((message['id']??0).toString())??0);", 1)
s = s.replace("if(type=='chat.message')_announceChatAlert(eventId:int.tryParse((d['event_id']??0).toString())??0,bookingId:bookingId,title:title,preview:body);",
              "if(type=='chat.message')_announceChatAlert(eventId:int.tryParse((d['event_id']??0).toString())??0,bookingId:bookingId,title:title,preview:body,messageId:int.tryParse((d['message_id']??0).toString())??0);", 1)
p.write_text(s)

# Chat UI: silent retry for transient DNS/network polling errors, friendly send errors,
# and poll-based audible fallback for incoming driver messages.
p = root / 'lib/screens/chat_screen.dart'
s = p.read_text()
field_old = '  bool _loading = true, _sending = false;\n  int _lastId = 0;\n  String? _error;\n'
field_new = '  bool _loading = true, _sending = false;\n  int _lastId = 0;\n  int _pollFailures = 0;\n  String? _error;\n'
if field_old not in s:
    raise SystemExit('passenger chat fields marker missing')
s = s.replace(field_old, field_new, 1)
start = s.find('  Future<void> _load({bool initial = false}) async {')
end = s.find('  Future<void> _send() async {', start)
if start < 0 or end < 0:
    raise SystemExit('passenger chat load markers missing')
new_load = r'''  Future<void> _load({bool initial = false}) async {
    try {
      final rows = await widget.session.chatMessages(widget.bookingId, afterId: initial ? 0 : _lastId);
      if (!mounted) return;
      for (final m in rows) {
        final isNew=_messages.every((x) => x.id != m.id);
        if (isNew) {
          _messages.add(m);
          if(!initial&&m.senderRole!='customer'){
            widget.session.notifyIncomingChatFromPoll(bookingId:widget.bookingId,messageId:m.id,senderName:m.senderName,preview:m.message);
          }
        }
        if (m.id > _lastId) _lastId = m.id;
      }
      _messages.sort((a, b) => a.id.compareTo(b.id));
      _pollFailures = 0;
      _error = null;
      if (rows.isNotEmpty) WidgetsBinding.instance.addPostFrameCallback((_) => _toBottom());
    } catch (_) {
      _pollFailures++;
      // A transient DNS / connectivity miss is expected on mobile hand-offs.
      // Keep cached messages and retry automatically instead of leaking SocketException.
      if(initial&&_messages.isEmpty&&_pollFailures>=2)_error='Connection interrupted. Retrying automatically…'.tr;
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

'''
s = s[:start] + new_load + s[end:]
start = s.find('  Future<void> _send() async {')
end = s.find('  void _toBottom()', start)
if start < 0 or end < 0:
    raise SystemExit('passenger chat send markers missing')
new_send = r'''  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      final m = await widget.session.sendChat(widget.bookingId, text);
      _controller.clear();
      if (_messages.every((x) => x.id != m.id)) _messages.add(m);
      if (m.id > _lastId) _lastId = m.id;
      _error = null;
      WidgetsBinding.instance.addPostFrameCallback((_) => _toBottom());
    } catch (_) {
      _error = 'Message could not be sent. Please try again.'.tr;
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

'''
s = s[:start] + new_send + s[end:]
p.write_text(s)

# Static release guards.
checks = {
    'lib/screens/quote_screen.dart': ['_pickupConfirmed', 'Fare recalculated. Confirm the new fare to continue.', 'await _performBooking(bookingVehicle)'],
    'lib/screens/chat_screen.dart': ['notifyIncomingChatFromPoll', '_pollFailures', 'Connection interrupted. Retrying automatically'],
    'lib/state/passenger_session.dart': ['_lastChatAlertMessageId', 'notifyIncomingChatFromPoll', 'messageId:int.tryParse'],
    'lib/config/app_config.dart': ["version = '0.6.3'"],
    'pubspec.yaml': ['version: 0.6.3+24'],
}
for rel, needles in checks.items():
    text=(root/rel).read_text()
    for needle in needles:
        if needle not in text:
            raise SystemExit(f'missing {needle} in {rel}')
print('Applied Passenger v0.6.3 booking/chat reliability fix.')
