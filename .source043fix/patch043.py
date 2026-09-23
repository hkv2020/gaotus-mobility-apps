from pathlib import Path

p = Path('passenger/pubspec.yaml')
x = p.read_text()
if 'version: 0.4.2+6' not in x:
    raise SystemExit('pubspec version contract missing')
p.write_text(x.replace('version: 0.4.2+6', 'version: 0.4.3+7'))

p = Path('passenger/lib/config/app_config.dart')
x = p.read_text()
p.write_text(x.replace("static const version = '0.4.2';", "static const version = '0.4.3';"))

p = Path('passenger/lib/screens/home_screen.dart')
x = p.read_text()
x = x.replace('Passenger v0.4.2', 'Passenger v0.4.3')
x = x.replace('Places suggestions + map fit fix', 'Pickup pin + Google suggestions + trip marker fix')
x = x.replace(
    "decoration: const InputDecoration(fillColor: Colors.transparent, prefixIcon: Icon(Icons.radio_button_checked, size: 18, color: Colors.blue), hintText: 'Pick-up location', border: InputBorder.none, enabledBorder: InputBorder.none, focusedBorder: InputBorder.none),",
    "decoration: const InputDecoration(fillColor: Colors.transparent, prefixIcon: Icon(Icons.radio_button_checked, size: 18, color: Colors.blue), suffixIcon: Icon(Icons.edit_location_alt_outlined), hintText: 'Pick-up location · tap to adjust pin', border: InputBorder.none, enabledBorder: InputBorder.none, focusedBorder: InputBorder.none),"
)
p.write_text(x)

p = Path('passenger/lib/screens/place_search_screen.dart')
x = p.read_text()
needle = "      if(loading)const LinearProgressIndicator(minHeight:2),\n"
insert = needle + "      if(controller.text.trim().length>=2&&!loading&&error==null) Padding(padding:const EdgeInsets.fromLTRB(20,8,20,4),child:Row(children:<Widget>[const Text('Google suggestions',style:TextStyle(fontWeight:FontWeight.w800)),const Spacer(),Text(suggestions.length.toString(),style:Theme.of(context).textTheme.bodySmall?.copyWith(color:AppTheme.softInk,fontWeight:FontWeight.w700))])),\n"
if needle not in x:
    raise SystemExit('place search contract missing')
p.write_text(x.replace(needle, insert, 1))

p = Path('passenger/lib/screens/trip_screen.dart')
x = p.read_text()
x = x.replace(
    "if (tracking != null && !const <String>{'completed','cancelled','canceled'}.contains(booking.status.toLowerCase()))",
    "if (driver != null && tracking != null && const <String>{'assigned','enroute','arrived','pob'}.contains(ride.status.toLowerCase()))"
)
x = x.replace(
    "if (pickup != null) Marker(point: pickup, width: 42, height: 42, child: const _TripPin(icon: Icons.circle, dark: true)),",
    "if (pickup != null) Marker(point: pickup, width: 42, height: 42, child: const _TripPin(icon: Icons.location_on_rounded, dark: true)),"
)
p.write_text(x)

assert 'version: 0.4.3+7' in Path('passenger/pubspec.yaml').read_text()
assert 'tap to adjust pin' in Path('passenger/lib/screens/home_screen.dart').read_text()
assert 'Google suggestions' in Path('passenger/lib/screens/place_search_screen.dart').read_text()
assert "driver != null && tracking != null" in Path('passenger/lib/screens/trip_screen.dart').read_text()
print('Passenger v0.4.3 patch applied')
