from pathlib import Path

root = Path('passenger')
loc = root / 'lib/core/localization.dart'
s = loc.read_text()
entries = {
    'pending': 'în așteptare',
    'assigned': 'alocată',
    'enroute': 'în drum',
    'arrived': 'ajuns',
    'pob': 'în desfășurare',
    'completed': 'finalizată',
    'cancelled': 'anulată',
    'failed': 'eșuată',
    'postponed': 'amânată',
}
needle = '\n  };\n  static String t('
missing = []
for key, value in entries.items():
    if f"'{key}':" not in s and f'"{key}":' not in s:
        missing.append(f"    '{key}': '{value}',")
if missing:
    s = s.replace(needle, '\n' + '\n'.join(missing) + needle, 1)
loc.write_text(s)

p = root / 'lib/screens/delivery_screen.dart'
s = p.read_text()
s = s.replace("StatusPill(label: job.status.toUpperCase(),", "StatusPill(label: job.status.tr.toUpperCase(),")
s = s.replace("${'Next'.tr} · ${next.operationLabel}", "${'Next'.tr} · ${next.operationLabel.tr}")
s = s.replace("${'Driver at'.tr} ${next?.operationLabel.toLowerCase()}", "${'Driver at'.tr} ${next?.operationLabel.tr.toLowerCase()}")
s = s.replace("${'Driver heading to'.tr} ${next?.operationLabel.toLowerCase()}", "${'Driver heading to'.tr} ${next?.operationLabel.tr.toLowerCase()}")
s = s.replace("stop.status.toUpperCase().tr", "stop.status.tr.toUpperCase()")
p.write_text(s)

p = root / 'lib/screens/trip_screen.dart'
s = p.read_text().replace("StatusPill(label: ride.status.toUpperCase(),", "StatusPill(label: ride.status.tr.toUpperCase(),")
p.write_text(s)

p = root / 'lib/screens/send_parcel_screen.dart'
s = p.read_text().replace("${deliveryQuote!.serviceLevelLabel} ·", "${deliveryQuote!.serviceLevelLabel.tr} ·")
p.write_text(s)

p = root / 'lib/widgets/booking_card.dart'
s = p.read_text().replace("Chip(label: Text(booking.status.toUpperCase()))", "Chip(label: Text(booking.status.tr.toUpperCase()))")
p.write_text(s)

p = root / 'lib/screens/home_screen.dart'
s = p.read_text().replace("'${ride.jobTypeLabel} #${ride.id}'", "'${ride.jobTypeLabel.tr} #${ride.id}'")
p.write_text(s)

print('Passenger final Romanian dynamic-label touch applied')
