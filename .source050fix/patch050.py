from pathlib import Path

p=Path('passenger/pubspec.yaml')
x=p.read_text()
if 'version: 0.4.6+10' not in x: raise SystemExit('v046 version missing')
p.write_text(x.replace('version: 0.4.6+10','version: 0.5.0+11',1))

p=Path('passenger/lib/config/app_config.dart')
x=p.read_text()
if "static const version = '0.4.6';" not in x: raise SystemExit('v046 config missing')
p.write_text(x.replace("static const version = '0.4.6';","static const version = '0.5.0';",1))

p=Path('passenger/lib/models/vehicle_quote.dart')
x=p.read_text()
x=x.replace(
"""  const VehicleQuote({required this.id, required this.title, required this.price, this.subtitle='', this.image='', this.passengers=0});""",
"""  const VehicleQuote({required this.id, required this.title, required this.price, this.subtitle='', this.image='', this.passengers=0, this.priceFormatted='', this.luggageLarge=0, this.luggageSmall=0});""",1)
x=x.replace(
"""  final int passengers;
  factory VehicleQuote.fromJson""",
"""  final int passengers;
  final String priceFormatted;
  final int luggageLarge;
  final int luggageSmall;
  String get priceLabel => priceFormatted.isNotEmpty ? priceFormatted : '£' + price.toStringAsFixed(2);
  factory VehicleQuote.fromJson""",1)
x=x.replace(
"""    passengers: (j['passengers'] as num?)?.toInt() ?? 0,
    price: (j['price'] as num?)?.toDouble() ?? double.tryParse((j['price'] ?? '').toString()) ?? 0,
""",
"""    passengers: (j['passengers'] as num?)?.toInt() ?? 0,
    price: (j['price'] as num?)?.toDouble() ?? double.tryParse((j['price'] ?? '').toString()) ?? 0,
    priceFormatted: (j['price_formatted'] ?? '').toString(),
    luggageLarge: (j['luggage_large'] as num?)?.toInt() ?? 0,
    luggageSmall: (j['luggage_small'] as num?)?.toInt() ?? 0,
""",1)
if 'priceFormatted' not in x: raise SystemExit('vehicle quote patch failed')
p.write_text(x)

p=Path('passenger/lib/screens/home_screen.dart')
x=p.read_text()
x=x.replace("Text('Where to?', style: Theme.of(context).textTheme.headlineMedium)","Text('Plan your ride', style: Theme.of(context).textTheme.headlineMedium)")
x=x.replace("Text('Passenger v0.4.6')","Text('Passenger v0.5.0')")
x=x.replace("Text('Pickup pin + Google suggestions + trip marker fix')","Text('Ride experience + route preview + inline suggestions')")
p.write_text(x)

quote=r'''import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/vehicle_quote.dart';
import '../state/passenger_session.dart';
import '../theme/app_theme.dart';
import '../widgets/premium.dart';
import 'trip_screen.dart';

class QuoteScreen extends StatefulWidget {
  const QuoteScreen({super.key, required this.session, required this.quote});
  final PassengerSession session;
  final FareQuote quote;
  @override State<QuoteScreen> createState()=>_QuoteScreenState();
}

class _QuoteScreenState extends State<QuoteScreen>{
  VehicleQuote? selected;
  String payment='online';

  @override void initState(){super.initState();if(widget.quote.vehicles.isNotEmpty)selected=widget.quote.vehicles.first;}

  Future<void> choosePayment() async{
    final value=await showModalBottomSheet<String>(
      context:context,showDragHandle:true,
      builder:(context)=>SafeArea(child:Padding(
        padding:const EdgeInsets.fromLTRB(20,6,20,20),
        child:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.stretch,children:<Widget>[
          Text('Payment method',style:Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height:16),
          ListTile(
            contentPadding:const EdgeInsets.symmetric(horizontal:4),
            leading:const CircleAvatar(backgroundColor:AppTheme.ink,child:Icon(Icons.credit_card,color:Colors.white)),
            title:const Text('Pay online',style:TextStyle(fontWeight:FontWeight.w800)),
            subtitle:const Text('Secure card payment'),
            trailing:payment=='online'?const Icon(Icons.check_circle,color:AppTheme.success):null,
            onTap:()=>Navigator.pop(context,'online'),
          ),
          ListTile(
            contentPadding:const EdgeInsets.symmetric(horizontal:4),
            leading:const CircleAvatar(backgroundColor:Color(0xFFF0F0ED),child:Icon(Icons.local_taxi_outlined,color:AppTheme.ink)),
            title:const Text('Pay in car',style:TextStyle(fontWeight:FontWeight.w800)),
            subtitle:const Text('Pay your driver at the end of the trip'),
            trailing:payment=='pay_in_car'?const Icon(Icons.check_circle,color:AppTheme.success):null,
            onTap:()=>Navigator.pop(context,'pay_in_car'),
          ),
        ]),
      )),
    );
    if(value!=null)setState(()=>payment=value);
  }

  Future<void> book() async{
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

  @override Widget build(BuildContext context){
    final j=widget.quote.journey;
    final pickup=_point(j['pickup_lat'],j['pickup_lng']);
    final dropoff=_point(j['dropoff_lat'],j['dropoff_lng']);
    final encoded=(j['route_polyline']??'').toString();
    final routePoints=_decodePolyline(encoded);
    final fitPoints=routePoints.length>=2?routePoints:<LatLng>[if(pickup!=null)pickup,if(dropoff!=null)dropoff];
    final initial=pickup??const LatLng(51.5074,-0.1278);

    final markers=<Marker>[
      if(pickup!=null)Marker(point:pickup,width:48,height:48,child:const _MapPin(icon:Icons.circle,dark:true)),
      if(dropoff!=null)Marker(point:dropoff,width:48,height:48,child:const _MapPin(icon:Icons.stop_rounded,dark:false)),
    ];

    return Scaffold(
      body:Stack(children:<Widget>[
        Positioned.fill(child:FlutterMap(
          options:MapOptions(
            initialCenter:initial,
            initialZoom:13,
            initialCameraFit:fitPoints.length>=2?CameraFit.bounds(
              bounds:LatLngBounds.fromPoints(fitPoints),
              padding:const EdgeInsets.fromLTRB(46,108,46,360),
              maxZoom:15,
            ):null,
          ),
          children:<Widget>[
            TileLayer(urlTemplate:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',userAgentPackageName:'com.gaotus.mobility.passenger'),
            if(routePoints.length>=2)PolylineLayer(polylines:<Polyline>[
              Polyline(points:routePoints,strokeWidth:5,color:AppTheme.ink,borderStrokeWidth:2,borderColor:Colors.white),
            ]),
            MarkerLayer(markers:markers),
          ],
        )),
        Positioned(
          top:MediaQuery.paddingOf(context).top+12,left:16,
          child:FloatingCircleButton(icon:Icons.arrow_back_rounded,onPressed:()=>Navigator.pop(context)),
        ),
        DraggableScrollableSheet(
          initialChildSize:.55,minChildSize:.38,maxChildSize:.88,snap:true,snapSizes:const <double>[.55,.88],
          builder:(context,controller)=>Container(
            decoration:const BoxDecoration(
              color:Colors.white,
              borderRadius:BorderRadius.vertical(top:Radius.circular(30)),
              boxShadow:<BoxShadow>[BoxShadow(color:Color(0x22000000),blurRadius:22,offset:Offset(0,-5))],
            ),
            child:ListView(
              controller:controller,
              padding:EdgeInsets.fromLTRB(20,0,20,MediaQuery.paddingOf(context).bottom+150),
              children:<Widget>[
                const SheetHandle(),
                Row(children:<Widget>[
                  Expanded(child:Text('Rides for you',style:Theme.of(context).textTheme.headlineSmall)),
                  if((j['duration_text']??'').toString().isNotEmpty)StatusPill(label:'Trip '+(j['duration_text']??'').toString()),
                ]),
                const SizedBox(height:6),
                Text(_journeySummary(j),style:Theme.of(context).textTheme.bodyMedium?.copyWith(color:AppTheme.softInk)),
                const SizedBox(height:14),
                _RouteSummary(journey:j),
                const SizedBox(height:18),
                Text('Recommended',style:Theme.of(context).textTheme.titleLarge),
                const SizedBox(height:8),
                ...widget.quote.vehicles.map((vehicle)=>_VehicleTile(
                  vehicle:vehicle,
                  selected:selected?.id==vehicle.id,
                  duration:(j['duration_text']??'').toString(),
                  onTap:()=>setState(()=>selected=vehicle),
                )),
                if(encoded.isEmpty)...<Widget>[
                  const SizedBox(height:8),
                  Text('Route line is unavailable from the map provider; distance and fare are still calculated by the platform.',style:Theme.of(context).textTheme.bodySmall),
                ],
              ],
            ),
          ),
        ),
      ]),
      bottomNavigationBar:_RideActionBar(
        payment:payment,
        selected:selected,
        busy:widget.session.busy,
        pickupTime:(j['pickup_time']??'').toString(),
        onPayment:choosePayment,
        onBook:book,
      ),
    );
  }

  String _journeySummary(Map<String,dynamic> j){
    final distance=(j['distance_text']??'').toString().trim();
    final date=(j['pickup_date']??'').toString().trim();
    final time=(j['pickup_time']??'').toString().trim();
    final bits=<String>[
      if(distance.isNotEmpty)distance,
      if(date.isNotEmpty||time.isNotEmpty)'$date $time'.trim(),
    ];
    return bits.join(' · ');
  }

  LatLng? _point(Object? lat,Object? lng){
    double? parse(Object? v)=>v is num?v.toDouble():double.tryParse((v??'').toString());
    final a=parse(lat),b=parse(lng);
    return a==null||b==null?null:LatLng(a,b);
  }

  List<LatLng> _decodePolyline(String encoded){
    if(encoded.isEmpty)return <LatLng>[];
    final points=<LatLng>[];var index=0;var lat=0;var lng=0;
    try{
      while(index<encoded.length){
        var result=0;var shift=0;int byte;
        do{byte=encoded.codeUnitAt(index++)-63;result|=(byte&0x1f)<<shift;shift+=5;}while(byte>=0x20&&index<encoded.length);
        final dLat=(result&1)!=0?~(result>>1):(result>>1);lat+=dLat;
        result=0;shift=0;
        do{byte=encoded.codeUnitAt(index++)-63;result|=(byte&0x1f)<<shift;shift+=5;}while(byte>=0x20&&index<encoded.length);
        final dLng=(result&1)!=0?~(result>>1):(result>>1);lng+=dLng;
        points.add(LatLng(lat/1e5,lng/1e5));
      }
    }catch(_){return <LatLng>[];}
    return points;
  }
}

class _RouteSummary extends StatelessWidget{
  const _RouteSummary({required this.journey});
  final Map<String,dynamic> journey;
  @override Widget build(BuildContext context)=>Container(
    padding:const EdgeInsets.symmetric(horizontal:14,vertical:8),
    decoration:BoxDecoration(color:const Color(0xFFF5F5F3),borderRadius:BorderRadius.circular(20)),
    child:Column(children:<Widget>[
      AddressRow(icon:const Icon(Icons.radio_button_checked,size:17,color:Colors.blue),title:(journey['pickup']??'Pick-up').toString(),subtitle:'Pick-up'),
      const Divider(),
      AddressRow(icon:const Icon(Icons.stop_rounded,size:18),title:(journey['dropoff']??'Destination').toString(),subtitle:'Destination'),
    ]),
  );
}

class _VehicleTile extends StatelessWidget{
  const _VehicleTile({required this.vehicle,required this.selected,required this.onTap,required this.duration});
  final VehicleQuote vehicle;final bool selected;final VoidCallback onTap;final String duration;
  @override Widget build(BuildContext context)=>Padding(
    padding:const EdgeInsets.only(bottom:9),
    child:InkWell(
      borderRadius:BorderRadius.circular(22),onTap:onTap,
      child:AnimatedContainer(
        duration:const Duration(milliseconds:170),
        padding:const EdgeInsets.fromLTRB(12,12,14,12),
        decoration:BoxDecoration(
          color:Colors.white,
          borderRadius:BorderRadius.circular(22),
          border:Border.all(color:selected?AppTheme.ink:Colors.transparent,width:selected?2.4:1),
        ),
        child:Row(children:<Widget>[
          SizedBox(width:88,height:62,child:vehicle.image.isNotEmpty
            ?Image.network(vehicle.image,fit:BoxFit.contain,errorBuilder:(_,__,___)=>const Icon(Icons.local_taxi_rounded,size:48))
            :const Icon(Icons.local_taxi_rounded,size:48)),
          const SizedBox(width:10),
          Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:<Widget>[
            Row(children:<Widget>[
              Flexible(child:Text(vehicle.title,maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(fontSize:19,fontWeight:FontWeight.w900))),
              if(vehicle.passengers>0)...<Widget>[
                const SizedBox(width:7),const Icon(Icons.person,size:15),const SizedBox(width:2),
                Text(vehicle.passengers.toString(),style:const TextStyle(fontSize:13,fontWeight:FontWeight.w800)),
              ],
            ]),
            const SizedBox(height:3),
            Text(duration.isEmpty?'Available for this journey':'Trip $duration',style:Theme.of(context).textTheme.bodyMedium?.copyWith(color:AppTheme.ink)),
            if(vehicle.subtitle.isNotEmpty)...<Widget>[
              const SizedBox(height:3),
              Text(vehicle.subtitle,maxLines:1,overflow:TextOverflow.ellipsis,style:Theme.of(context).textTheme.bodySmall),
            ],
          ])),
          const SizedBox(width:10),
          Column(crossAxisAlignment:CrossAxisAlignment.end,children:<Widget>[
            Text(vehicle.priceLabel,style:const TextStyle(fontSize:19,fontWeight:FontWeight.w900)),
            if(selected)const Padding(padding:EdgeInsets.only(top:7),child:Icon(Icons.check_circle,size:19,color:AppTheme.success)),
          ]),
        ]),
      ),
    ),
  );
}

class _RideActionBar extends StatelessWidget{
  const _RideActionBar({required this.payment,required this.selected,required this.busy,required this.pickupTime,required this.onPayment,required this.onBook});
  final String payment;final VehicleQuote? selected;final bool busy;final String pickupTime;final VoidCallback onPayment;final VoidCallback onBook;

  @override Widget build(BuildContext context)=>Material(
    color:Colors.white,elevation:18,
    child:SafeArea(top:false,child:Padding(
      padding:const EdgeInsets.fromLTRB(18,10,18,12),
      child:Column(mainAxisSize:MainAxisSize.min,children:<Widget>[
        InkWell(
          borderRadius:BorderRadius.circular(14),onTap:onPayment,
          child:Padding(
            padding:const EdgeInsets.symmetric(vertical:8),
            child:Row(children:<Widget>[
              Container(
                width:38,height:30,
                decoration:BoxDecoration(color:payment=='online'?AppTheme.ink:const Color(0xFFF0F0ED),borderRadius:BorderRadius.circular(8)),
                child:Icon(payment=='online'?Icons.credit_card_rounded:Icons.local_taxi_outlined,color:payment=='online'?Colors.white:AppTheme.ink,size:20),
              ),
              const SizedBox(width:12),
              Expanded(child:Text(payment=='online'?'Pay online':'Pay in car',style:const TextStyle(fontWeight:FontWeight.w900,fontSize:16))),
              if(pickupTime.isNotEmpty)Padding(padding:const EdgeInsets.only(right:8),child:Text(pickupTime,style:Theme.of(context).textTheme.bodySmall)),
              const Icon(Icons.chevron_right_rounded),
            ]),
          ),
        ),
        const SizedBox(height:4),
        FilledButton(
          onPressed:busy||selected==null?null:onBook,
          child:busy
            ?const SizedBox(width:22,height:22,child:CircularProgressIndicator(strokeWidth:2.3,color:Colors.white))
            :Text(selected==null?'Choose a ride':'Choose '+selected!.title),
        ),
      ]),
    )),
  );
}

class _MapPin extends StatelessWidget{
  const _MapPin({required this.icon,required this.dark});
  final IconData icon;final bool dark;
  @override Widget build(BuildContext context)=>Container(
    decoration:BoxDecoration(
      color:dark?AppTheme.ink:Colors.white,
      shape:BoxShape.circle,
      border:Border.all(color:AppTheme.ink,width:2),
      boxShadow:const <BoxShadow>[BoxShadow(color:Color(0x33000000),blurRadius:8)],
    ),
    child:Icon(icon,color:dark?Colors.white:AppTheme.ink,size:18),
  );
}
'''
Path('passenger/lib/screens/quote_screen.dart').write_text(quote)

assert 'version: 0.5.0+11' in Path('passenger/pubspec.yaml').read_text()
assert "static const version = '0.5.0';" in Path('passenger/lib/config/app_config.dart').read_text()
assert 'priceFormatted' in Path('passenger/lib/models/vehicle_quote.dart').read_text()
assert 'route_polyline' in Path('passenger/lib/screens/quote_screen.dart').read_text()
assert 'PolylineLayer' in Path('passenger/lib/screens/quote_screen.dart').read_text()
assert '_RideActionBar' in Path('passenger/lib/screens/quote_screen.dart').read_text()
assert 'Plan your ride' in Path('passenger/lib/screens/home_screen.dart').read_text()
assert 'destinationChanged' in Path('passenger/lib/screens/home_screen.dart').read_text()
print('Passenger v0.5.0 Ride Experience patch applied')
