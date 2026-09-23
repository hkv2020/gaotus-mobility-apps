from pathlib import Path

p=Path('passenger/pubspec.yaml')
x=p.read_text()
if 'version: 0.5.0+11' not in x: raise SystemExit('v050 version missing')
p.write_text(x.replace('version: 0.5.0+11','version: 0.5.1+12',1))

p=Path('passenger/lib/config/app_config.dart')
x=p.read_text()
if "static const version = '0.5.0';" not in x: raise SystemExit('v050 config missing')
p.write_text(x.replace("static const version = '0.5.0';","static const version = '0.5.1';",1))

p=Path('passenger/lib/screens/home_screen.dart')
x=p.read_text()
x=x.replace("Text('Passenger v0.5.0')","Text('Passenger v0.5.1')")
x=x.replace("Text('Ride experience + route preview + inline suggestions')","Text('Pickup confirmation + adaptive ride sheet')")
p.write_text(x)

p=Path('passenger/lib/screens/quote_screen.dart')
x=p.read_text()

x=x.replace(
"import '../models/vehicle_quote.dart';\n",
"import '../models/vehicle_quote.dart';\nimport '../models/place_selection.dart';\n",1)
x=x.replace(
"import 'trip_screen.dart';\n",
"import 'trip_screen.dart';\nimport 'pickup_confirm_screen.dart';\n",1)

x=x.replace(
"""class _QuoteScreenState extends State<QuoteScreen>{
  VehicleQuote? selected;
  String payment='online';

  @override void initState(){super.initState();if(widget.quote.vehicles.isNotEmpty)selected=widget.quote.vehicles.first;}
""",
"""class _QuoteScreenState extends State<QuoteScreen>{
  VehicleQuote? selected;
  String payment='online';
  late FareQuote currentQuote;

  @override void initState(){
    super.initState();
    currentQuote=widget.quote;
    if(currentQuote.vehicles.isNotEmpty)selected=currentQuote.vehicles.first;
  }
""",1)

old_book="""  Future<void> book() async{
    final vehicle=selected;if(vehicle==null)return;
    try{
      final booking=await widget.session.createBooking(vehicle,paymentMethod:payment);
      final p=booking.payment;
      final url=p['payment_url']?.toString();
      if(payment=='online'&&url!=null&&url.isNotEmpty)await launchUrl(Uri.parse(url),mode:LaunchMode.externalApplication);
      if(mounted){
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder:(_)=>TripScreen(session:widget.session,bookingId:booking.id)),
          (route)=>route.isFirst,
        );
      }
    }catch(error){
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('$error')));
    }
  }
"""
new_book="""  Future<void> book() async{
    final vehicle=selected;
    if(vehicle==null)return;

    final j=currentQuote.journey;
    final original=_point(j['pickup_lat'],j['pickup_lng']);
    if(original==null){
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
    if(moved){
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
        setState((){
          currentQuote=refreshed;
          selected=same??(refreshed.vehicles.isNotEmpty?refreshed.vehicles.first:null);
        });
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Pick-up updated. Fare recalculated — confirm your ride again.')));
      }catch(error){
        if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('$error')));
      }
      return;
    }

    await _performBooking(vehicle);
  }

  Future<void> _performBooking(VehicleQuote vehicle) async{
    try{
      final booking=await widget.session.createBooking(vehicle,paymentMethod:payment);
      final p=booking.payment;
      final url=p['payment_url']?.toString();
      if(payment=='online'&&url!=null&&url.isNotEmpty)await launchUrl(Uri.parse(url),mode:LaunchMode.externalApplication);
      if(mounted){
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder:(_)=>TripScreen(session:widget.session,bookingId:booking.id)),
          (route)=>route.isFirst,
        );
      }
    }catch(error){
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('$error')));
    }
  }
"""
if old_book not in x: raise SystemExit('v050 booking contract missing')
x=x.replace(old_book,new_book,1)

x=x.replace("    final j=widget.quote.journey;","    final j=currentQuote.journey;",1)
x=x.replace("                ...widget.quote.vehicles.map((vehicle)=>_VehicleTile(","                ...currentQuote.vehicles.map((vehicle)=>_VehicleTile(",1)
x=x.replace("                Text('Recommended',style:Theme.of(context).textTheme.titleLarge),","                Text(currentQuote.vehicles.length==1?'Available ride':'Recommended',style:Theme.of(context).textTheme.titleLarge),",1)

x=x.replace(
"""        DraggableScrollableSheet(
          initialChildSize:.55,minChildSize:.38,maxChildSize:.88,snap:true,snapSizes:const <double>[.55,.88],
""",
"""        DraggableScrollableSheet(
          initialChildSize:.55,
          minChildSize:.38,
          maxChildSize:currentQuote.vehicles.length<=2 ? .70 : .88,
          snap:true,
          snapSizes:currentQuote.vehicles.length<=2 ? const <double>[.55,.70] : const <double>[.55,.88],
""",1)

old_summary="""  String _journeySummary(Map<String,dynamic> j){
    final distance=(j['distance_text']??'').toString().trim();
    final date=(j['pickup_date']??'').toString().trim();
    final time=(j['pickup_time']??'').toString().trim();
    final bits=<String>[
      if(distance.isNotEmpty)distance,
      if(date.isNotEmpty||time.isNotEmpty)'$date $time'.trim(),
    ];
    return bits.join(' · ');
  }
"""
new_summary="""  String _journeySummary(Map<String,dynamic> j){
    final distance=(j['distance_text']??'').toString().trim();
    final schedule=_scheduleLabel(j);
    return <String>[if(distance.isNotEmpty)distance,if(schedule.isNotEmpty)schedule].join(' · ');
  }

  String _scheduleLabel(Map<String,dynamic> j){
    final date=(j['pickup_date']??'').toString().trim();
    final time=(j['pickup_time']??'').toString().trim();
    if(date.isEmpty&&time.isEmpty)return '';
    try{
      final dt=DateTime.parse(date+' '+(time.isEmpty?'00:00':time));
      final now=DateTime.now();
      final delta=dt.difference(now).inMinutes.abs();
      if(delta<=20)return 'Now';
      final sameDay=dt.year==now.year&&dt.month==now.month&&dt.day==now.day;
      if(sameDay)return 'Today '+time;
      const months=<String>['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      return dt.day.toString()+' '+months[dt.month-1]+' · '+time;
    }catch(_){
      return (date+' '+time).trim();
    }
  }
"""
if old_summary not in x: raise SystemExit('journey summary contract missing')
x=x.replace(old_summary,new_summary,1)

x=x.replace("        pickupTime:(j['pickup_time']??'').toString(),","        pickupTime:_scheduleLabel(j),",1)

p.write_text(x)

assert 'version: 0.5.1+12' in Path('passenger/pubspec.yaml').read_text()
assert "static const version = '0.5.1';" in Path('passenger/lib/config/app_config.dart').read_text()
quote=Path('passenger/lib/screens/quote_screen.dart').read_text()
assert 'PickupConfirmScreen' in quote
assert 'Pick-up updated. Fare recalculated' in quote
assert 'currentQuote.vehicles.length<=2 ? .70 : .88' in quote
assert "if(delta<=20)return 'Now';" in quote
assert 'destinationChanged' in Path('passenger/lib/screens/home_screen.dart').read_text()
print('Passenger v0.5.1 pickup confirmation patch applied')
