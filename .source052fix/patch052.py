from pathlib import Path

p=Path('passenger/pubspec.yaml')
x=p.read_text()
if 'version: 0.5.1+12' not in x: raise SystemExit('v051 version missing')
p.write_text(x.replace('version: 0.5.1+12','version: 0.5.2+13',1))

p=Path('passenger/lib/config/app_config.dart')
x=p.read_text()
if "static const version = '0.5.1';" not in x: raise SystemExit('v051 config missing')
p.write_text(x.replace("static const version = '0.5.1';","static const version = '0.5.2';",1))

p=Path('passenger/lib/screens/home_screen.dart')
x=p.read_text()
x=x.replace("Text('Passenger v0.5.1')","Text('Passenger v0.5.2')")
x=x.replace("Text('Pickup confirmation + adaptive ride sheet')","Text('Passenger ride catalog + grouped ride options')")
p.write_text(x)

p=Path('passenger/lib/models/vehicle_quote.dart')
x=p.read_text()
if "this.luggageSmall=0});" not in x:
    raise SystemExit('vehicle quote constructor contract missing')
x=x.replace(
    "this.luggageSmall=0});",
    "this.luggageSmall=0, this.group='recommended', this.badge='', this.sortOrder=0});",
    1
)
if "  final int luggageSmall;\n  String get priceLabel" not in x:
    raise SystemExit('vehicle quote fields contract missing')
x=x.replace(
    "  final int luggageSmall;\n  String get priceLabel",
    "  final int luggageSmall;\n  final String group;\n  final String badge;\n  final int sortOrder;\n  String get priceLabel",
    1
)
price_line="    price: (j['price'] as num?)?.toDouble() ?? double.tryParse('${j['price']}') ?? 0,"
if price_line not in x:
    raise SystemExit('vehicle quote price parser contract missing')
x=x.replace(
    price_line,
    price_line+"\n    priceFormatted: (j['price_formatted'] ?? '').toString(),\n    luggageLarge: (j['luggage_large'] as num?)?.toInt() ?? 0,\n    luggageSmall: (j['luggage_small'] as num?)?.toInt() ?? 0,\n    group: (j['group'] ?? 'recommended').toString(),\n    badge: (j['badge'] ?? '').toString(),\n    sortOrder: (j['sort_order'] as num?)?.toInt() ?? 0,",
    1
)
if "final String group;" not in x or "badge:" not in x or "priceFormatted:" not in x:
    raise SystemExit('vehicle catalog model patch failed')
p.write_text(x)

p=Path('passenger/lib/screens/quote_screen.dart')
x=p.read_text()
old="""    final j=currentQuote.journey;
    final pickup=_point(j['pickup_lat'],j['pickup_lng']);
"""
new="""    final j=currentQuote.journey;
    final recommendedVehicles=currentQuote.vehicles.where((v)=>v.group!='more_options').toList();
    final moreOptionsVehicles=currentQuote.vehicles.where((v)=>v.group=='more_options').toList();
    final pickup=_point(j['pickup_lat'],j['pickup_lng']);
"""
if old not in x: raise SystemExit('quote build insertion point missing')
x=x.replace(old,new,1)

old_list="""                Text(currentQuote.vehicles.length==1?'Available ride':'Recommended',style:Theme.of(context).textTheme.titleLarge),
                const SizedBox(height:8),
                ...currentQuote.vehicles.map((vehicle)=>_VehicleTile(
                  vehicle:vehicle,
                  selected:selected?.id==vehicle.id,
                  duration:(j['duration_text']??'').toString(),
                  onTap:()=>setState(()=>selected=vehicle),
                )),
                if(encoded.isEmpty)...<Widget>[
"""
new_list="""                if(recommendedVehicles.isNotEmpty)...<Widget>[
                  Text(currentQuote.vehicles.length==1?'Available ride':'Recommended',style:Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height:8),
                  ...recommendedVehicles.map((vehicle)=>_VehicleTile(
                    vehicle:vehicle,
                    selected:selected?.id==vehicle.id,
                    duration:(j['duration_text']??'').toString(),
                    onTap:()=>setState(()=>selected=vehicle),
                  )),
                ],
                if(moreOptionsVehicles.isNotEmpty)...<Widget>[
                  const SizedBox(height:12),
                  Text('More options',style:Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height:8),
                  ...moreOptionsVehicles.map((vehicle)=>_VehicleTile(
                    vehicle:vehicle,
                    selected:selected?.id==vehicle.id,
                    duration:(j['duration_text']??'').toString(),
                    onTap:()=>setState(()=>selected=vehicle),
                  )),
                ],
                if(encoded.isEmpty)...<Widget>[
"""
if old_list not in x: raise SystemExit('ride list block missing')
x=x.replace(old_list,new_list,1)

old_title="""            Row(children:<Widget>[
              Flexible(child:Text(vehicle.title,maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(fontSize:19,fontWeight:FontWeight.w900))),
              if(vehicle.passengers>0)...<Widget>[
                const SizedBox(width:7),const Icon(Icons.person,size:15),const SizedBox(width:2),
                Text(vehicle.passengers.toString(),style:const TextStyle(fontSize:13,fontWeight:FontWeight.w800)),
              ],
            ]),
"""
new_title="""            Row(children:<Widget>[
              Flexible(child:Text(vehicle.title,maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(fontSize:19,fontWeight:FontWeight.w900))),
              if(vehicle.passengers>0)...<Widget>[
                const SizedBox(width:7),const Icon(Icons.person,size:15),const SizedBox(width:2),
                Text(vehicle.passengers.toString(),style:const TextStyle(fontSize:13,fontWeight:FontWeight.w800)),
              ],
            ]),
            if(vehicle.badge.isNotEmpty)...<Widget>[
              const SizedBox(height:4),
              Container(
                padding:const EdgeInsets.symmetric(horizontal:8,vertical:3),
                decoration:BoxDecoration(color:const Color(0xFFF0F0ED),borderRadius:BorderRadius.circular(999)),
                child:Text(vehicle.badge,maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(fontSize:11,fontWeight:FontWeight.w800)),
              ),
            ],
"""
if old_title not in x: raise SystemExit('vehicle title block missing')
x=x.replace(old_title,new_title,1)

p.write_text(x)

assert 'version: 0.5.2+13' in Path('passenger/pubspec.yaml').read_text()
assert "static const version = '0.5.2';" in Path('passenger/lib/config/app_config.dart').read_text()
vehicle=Path('passenger/lib/models/vehicle_quote.dart').read_text()
quote=Path('passenger/lib/screens/quote_screen.dart').read_text()
assert "final String group;" in vehicle
assert "final String badge;" in vehicle
assert "More options" in quote
assert "recommendedVehicles" in quote
assert "vehicle.badge.isNotEmpty" in quote
assert 'PickupConfirmScreen' in quote
assert 'destinationChanged' in Path('passenger/lib/screens/home_screen.dart').read_text()
print('Passenger v0.5.2 passenger ride catalog patch applied')
