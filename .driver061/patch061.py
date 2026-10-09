from pathlib import Path

root = Path('driver')

def text(rel):
    return (root / rel).read_text()

def write(rel, value):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(value)

def replace(rel, old, new, label):
    p = root / rel
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'{label}: marker missing in {rel}')
    p.write_text(s.replace(old, new, 1))

def add_import(rel, import_line):
    p = root / rel
    s = p.read_text()
    if import_line in s:
        return
    lines = s.splitlines()
    insert = 0
    for i, line in enumerate(lines):
        if line.startswith('import '):
            insert = i + 1
    lines.insert(insert, import_line)
    p.write_text('\n'.join(lines) + ('\n' if s.endswith('\n') else ''))

# Shared country/currency runtime. Platform v1.5.0 sends this through /driver/app-hub.
write('lib/core/country_config.dart', r'''class CountryConfig {
  CountryConfig._();

  static String code = 'GB';
  static String currency = 'GBP';
  static String symbol = '£';
  static String locale = 'en_GB';
  static String timezone = 'Europe/London';
  static String phonePrefix = '+44';
  static String units = 'imperial';

  static void configure(Map<String, dynamic>? raw) {
    if (raw == null || raw.isEmpty) return;
    final nextCode = (raw['country'] ?? raw['code'] ?? code).toString().trim().toUpperCase();
    final nextCurrency = (raw['currency'] ?? currency).toString().trim().toUpperCase();
    final nextSymbol = (raw['currency_symbol'] ?? raw['symbol'] ?? symbol).toString().trim();
    code = nextCode.isEmpty ? code : nextCode;
    currency = nextCurrency.isEmpty ? currency : nextCurrency;
    symbol = nextSymbol.isEmpty ? _symbolFor(currency) : nextSymbol;
    locale = (raw['locale'] ?? locale).toString();
    timezone = (raw['timezone'] ?? timezone).toString();
    phonePrefix = (raw['phone_prefix'] ?? phonePrefix).toString();
    units = (raw['units'] ?? units).toString();
  }

  static String _symbolFor(String code) {
    switch (code.toUpperCase()) {
      case 'GBP': return '£';
      case 'EUR': return '€';
      case 'USD': return r'$';
      case 'RON': return 'lei';
      default: return code.toUpperCase();
    }
  }

  static String get currencyInputLabel => currency == 'RON' ? 'lei' : (symbol.isEmpty ? currency : symbol);

  static String money(num value, {String? currencyCode}) {
    final code = (currencyCode == null || currencyCode.trim().isEmpty ? currency : currencyCode).toUpperCase();
    final amount = value.toStringAsFixed(2);
    if (code == 'RON') return '$amount lei';
    final s = code == currency ? symbol : _symbolFor(code);
    if (s.isEmpty) return '$amount $code';
    if (s.length > 3) return '$amount $s';
    return '$s$amount';
  }
}
''')

replace('pubspec.yaml', 'version: 0.6.0+15', 'version: 0.6.1+16', 'pubspec version')
replace('lib/config/app_config.dart', "static const String version = '0.6.0';", "static const String version = '0.6.1';", 'app version')

add_import('lib/state/app_session.dart', "import '../core/country_config.dart';")
replace('lib/state/app_session.dart',
        "  Map<String, dynamic> get driverPreferences => mapValue(driverHub['preferences']);\n",
        "  Map<String, dynamic> get driverPreferences => mapValue(driverHub['preferences']);\n  Map<String, dynamic> get countryConfig => mapValue(driverHub['country']);\n  String get countryCurrency => (countryConfig['currency'] ?? CountryConfig.currency).toString().toUpperCase();\n  String get countryCurrencySymbol => (countryConfig['currency_symbol'] ?? CountryConfig.symbol).toString();\n  String money(num value, {String? currency}) => CountryConfig.money(value, currencyCode: currency ?? countryCurrency);\n",
        'country getters')
replace('lib/state/app_session.dart',
        "      driverHub = await api.driverAppHub();\n      hubError = null;",
        "      driverHub = await api.driverAppHub();\n      CountryConfig.configure(mapValue(driverHub['country']));\n      hubError = null;",
        'hub country configure')
replace('lib/state/app_session.dart',
        "        driverHub = hub;\n      } else {",
        "        driverHub = hub;\n        CountryConfig.configure(mapValue(driverHub['country']));\n      } else {",
        'saved hub country configure')

# Job/ride extras and active fare.
add_import('lib/screens/job_screen.dart', "import '../core/country_config.dart';")
replace('lib/screens/job_screen.dart', "decoration: const InputDecoration(labelText: 'Unit amount (£)'),", "decoration: InputDecoration(labelText: 'Unit amount (${CountryConfig.currencyInputLabel})'),", 'extra amount label')
replace('lib/screens/job_screen.dart', "content: Text('${extra.label} · £${extra.lineTotal.toStringAsFixed(2)}'),", "content: Text('${extra.label} · ${CountryConfig.money(extra.lineTotal)}'),", 'remove extra amount')
replace('lib/screens/job_screen.dart', "? 'Extras total: £${session.tripExtrasTotal.toStringAsFixed(2)}. The saved payment method will be attempted; otherwise the customer receives an invoice.'", "? 'Extras total: ${CountryConfig.money(session.tripExtrasTotal)}. The saved payment method will be attempted; otherwise the customer receives an invoice.'", 'extras completion total')
replace('lib/screens/job_screen.dart', "final amount = result.amount > 0 ? '\\nExtras: £${result.amount.toStringAsFixed(2)}' : '';", "final amount = result.amount > 0 ? '\\nExtras: ${CountryConfig.money(result.amount)}' : '';", 'completion amount')
replace('lib/screens/job_screen.dart', "Text('£${job.total.toStringAsFixed(2)}', style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),", "Text(CountryConfig.money(job.total), style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),", 'job fare')
replace('lib/screens/job_screen.dart', "subtitle: Text('${extra.qty} × £${extra.unit.toStringAsFixed(2)}'),", "subtitle: Text('${extra.qty} × ${CountryConfig.money(extra.unit)}'),", 'extra unit amount')
replace('lib/screens/job_screen.dart', "Text('£${extra.lineTotal.toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.w900)),", "Text(CountryConfig.money(extra.lineTotal), style: const TextStyle(fontWeight: FontWeight.w900)),", 'extra line total')
replace('lib/screens/job_screen.dart', "Row(children: <Widget>[const Expanded(child: Text('Extras total', style: TextStyle(fontWeight: FontWeight.w800))), Text('£${total.toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.w900))]),", "Row(children: <Widget>[const Expanded(child: Text('Extras total', style: TextStyle(fontWeight: FontWeight.w800))), Text(CountryConfig.money(total), style: const TextStyle(fontWeight: FontWeight.w900))]),", 'extras panel total')

# Logistics COD.
add_import('lib/screens/operations_job_screen.dart', "import '../core/country_config.dart';")
replace('lib/screens/operations_job_screen.dart', "if (stop.codAmount > 0) _Chip(text: 'COD £${stop.codAmount.toStringAsFixed(2)}'),", "if (stop.codAmount > 0) _Chip(text: 'COD ${CountryConfig.money(stop.codAmount)}'),", 'COD amount')

# Offer card + local notification.
add_import('lib/widgets/offer_card.dart', "import '../core/country_config.dart';")
replace('lib/widgets/offer_card.dart', "Text('£${job.total.toStringAsFixed(2)}', style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w900)),", "Text(CountryConfig.money(job.total), style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w900)),", 'offer price')
add_import('lib/services/offer_notification_service.dart', "import '../core/country_config.dart';")
replace('lib/services/offer_notification_service.dart', "final price = total > 0 ? ' · £${total.toStringAsFixed(2)}' : '';", "final price = total > 0 ? ' · ${CountryConfig.money(total)}' : '';", 'notification price')

# Earnings use server currency when supplied, country pack as fallback. RON is displayed naturally as a lei suffix.
add_import('lib/models/earnings_summary.dart', "import '../core/country_config.dart';")
replace('lib/models/earnings_summary.dart', "currency: (json['currency'] ?? 'GBP').toString(),", "currency: (json['currency'] ?? CountryConfig.currency).toString(),", 'earnings currency fallback')
replace('lib/screens/driver_home_screen.dart', "final currency = today?.currency ?? 'GBP';", "final currency = today?.currency ?? session.countryCurrency;", 'home currency fallback')
replace('lib/screens/driver_home_screen.dart', "    return '$symbol${value.toStringAsFixed(2)}';", "    return currency.toUpperCase() == 'RON' ? '${value.toStringAsFixed(2)} lei' : '$symbol${value.toStringAsFixed(2)}';", 'home RON format')
replace('lib/screens/earnings_screen.dart', "    return '$symbol${value.toStringAsFixed(2)}';", "    return currency.toUpperCase() == 'RON' ? '${value.toStringAsFixed(2)} lei' : '$symbol${value.toStringAsFixed(2)}';", 'earnings RON format')

# No operational screen is allowed to keep a hard-coded Pound marker after the country-aware patch.
for rel in [
    'lib/screens/job_screen.dart',
    'lib/screens/operations_job_screen.dart',
    'lib/widgets/offer_card.dart',
    'lib/services/offer_notification_service.dart',
]:
    if '£' in text(rel):
        raise SystemExit(f'hard-coded Pound remains in {rel}')

print('Applied Driver v0.6.1 Country Aware patch.')
