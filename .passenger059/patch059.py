from pathlib import Path

root = Path('passenger')

def write(rel, value):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(value)

def replace(rel, old, new, label):
    p=root/rel; s=p.read_text()
    if old not in s: raise SystemExit(f'{label}: marker missing in {rel}')
    p.write_text(s.replace(old,new,1))

def add_import(rel, line):
    p=root/rel; s=p.read_text()
    if line in s: return
    lines=s.splitlines(); idx=0
    for i,v in enumerate(lines):
        if v.startswith('import '): idx=i+1
    lines.insert(idx,line)
    p.write_text('\n'.join(lines)+('\n' if s.endswith('\n') else ''))

write('lib/core/country_config.dart', r'''class CountryConfig {
  CountryConfig._();

  static String code = 'GB';
  static String currency = 'GBP';
  static String symbol = '£';
  static String locale = 'en_GB';
  static String timezone = 'Europe/London';
  static String phonePrefix = '+44';
  static String units = 'imperial';

  static void reset() {
    code = 'GB'; currency = 'GBP'; symbol = '£'; locale = 'en_GB';
    timezone = 'Europe/London'; phonePrefix = '+44'; units = 'imperial';
  }

  static void configure(Map<String, dynamic>? raw) {
    if (raw == null || raw.isEmpty) return;
    final c=(raw['country'] ?? raw['code'] ?? code).toString().trim().toUpperCase();
    final cur=(raw['currency'] ?? currency).toString().trim().toUpperCase();
    final sym=(raw['currency_symbol'] ?? raw['symbol'] ?? symbol).toString().trim();
    if(c.isNotEmpty) code=c;
    if(cur.isNotEmpty) currency=cur;
    symbol=sym.isEmpty?_symbolFor(currency):sym;
    locale=(raw['locale'] ?? locale).toString();
    timezone=(raw['timezone'] ?? timezone).toString();
    phonePrefix=(raw['phone_prefix'] ?? phonePrefix).toString();
    units=(raw['units'] ?? units).toString();
  }

  static String _symbolFor(String value) {
    switch(value.toUpperCase()) {
      case 'GBP': return '£';
      case 'EUR': return '€';
      case 'USD': return r'$';
      case 'RON': return 'lei';
      default: return value.toUpperCase();
    }
  }

  static String money(num value,{String? currencyCode}) {
    final cur=(currencyCode==null||currencyCode.trim().isEmpty?currency:currencyCode).toUpperCase();
    final amount=value.toStringAsFixed(2);
    if(cur=='RON') return '$amount lei';
    final s=cur==currency?symbol:_symbolFor(cur);
    if(s.isEmpty) return '$amount $cur';
    if(s.length>3) return '$amount $s';
    return '$s$amount';
  }
}
''')

replace('pubspec.yaml','version: 0.5.8+19','version: 0.5.9+20','pubspec version')
replace('lib/config/app_config.dart',"static const version = '0.5.8';","static const version = '0.5.9';",'app version')

add_import('lib/state/passenger_session.dart',"import '../core/country_config.dart';")
# Add runtime country state near identity when possible.
replace('lib/state/passenger_session.dart',
        'Map<String,dynamic>? identity;',
        "Map<String,dynamic>? identity;\n  Map<String,dynamic> country=<String,dynamic>{};\n  String get countryCurrency => (country['currency'] ?? CountryConfig.currency).toString().toUpperCase();\n  String get countryCurrencySymbol => (country['currency_symbol'] ?? CountryConfig.symbol).toString();\n  String money(num value,{String? currency}) => CountryConfig.money(value,currencyCode: currency ?? countryCurrency);",
        'country state')
replace('lib/state/passenger_session.dart',
        "Future<void> _validateAndLoad() async {final api=_api!;final m=await api.me();identity=m['user'] is Map?Map<String,dynamic>.from(m['user'] as Map):null;await refreshBookings(silent:true,connectRealtime:false,propagateErrors:true);}",
        "Future<void> _validateAndLoad() async {final api=_api!;final m=await api.me();identity=m['user'] is Map?Map<String,dynamic>.from(m['user'] as Map):null;final rawCountry=m['country'];country=rawCountry is Map?Map<String,dynamic>.from(rawCountry):<String,dynamic>{};CountryConfig.configure(country);await refreshBookings(silent:true,connectRealtime:false,propagateErrors:true);}",
        'auth me country')
replace('lib/state/passenger_session.dart',
        'identity=null;bookings=[];',
        'identity=null;country=<String,dynamic>{};CountryConfig.reset();bookings=[];',
        'logout country reset')

# Visible ride pricing should follow the platform-selected country.
add_import('lib/screens/home_screen.dart',"import '../core/country_config.dart';")
replace('lib/screens/home_screen.dart',
        "? '${ride.pickupDate} ${ride.pickupTime} · £${ride.total.toStringAsFixed(2)}'",
        "? '${ride.pickupDate} ${ride.pickupTime} · ${CountryConfig.money(ride.total)}'",
        'home history fare')
add_import('lib/screens/trip_screen.dart',"import '../core/country_config.dart';")
replace('lib/screens/trip_screen.dart',
        "subtitle: '$vehicleName · £${ride.total.toStringAsFixed(2)}'",
        "subtitle: '$vehicleName · ${CountryConfig.money(ride.total)}'",
        'trip fare')
add_import('lib/models/vehicle_quote.dart',"import '../core/country_config.dart';")
replace('lib/models/vehicle_quote.dart',
        "String get priceLabel => priceFormatted.isNotEmpty ? priceFormatted : '£' + price.toStringAsFixed(2);",
        "String get priceLabel => priceFormatted.isNotEmpty ? priceFormatted : CountryConfig.money(price);",
        'vehicle quote fallback')
add_import('lib/widgets/booking_card.dart',"import '../core/country_config.dart';")
replace('lib/widgets/booking_card.dart',
        "'£${booking.total.toStringAsFixed(2)} · ${booking.pickupDate} ${booking.pickupTime}',",
        "'${CountryConfig.money(booking.total)} · ${booking.pickupDate} ${booking.pickupTime}',",
        'booking card fare')

for rel in ['lib/screens/home_screen.dart','lib/screens/trip_screen.dart','lib/models/vehicle_quote.dart','lib/widgets/booking_card.dart']:
    if '£' in (root/rel).read_text():
        raise SystemExit(f'hard-coded Pound remains in {rel}')

print('Applied Passenger v0.5.9 Country Aware patch.')
