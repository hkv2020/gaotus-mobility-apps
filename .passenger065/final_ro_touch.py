from pathlib import Path
import re

root = Path('passenger')
loc = root / 'lib/core/localization.dart'
s = loc.read_text()

# De-duplicate Romanian dictionary keys after the broad UI sweep.
# Keep the LAST occurrence so the newer v0.6.5 wording wins over older pack entries.
lines = s.splitlines()
start = next((i for i, line in enumerate(lines) if '_ro' in line and 'Map<' in line and '{' in line), None)
if start is not None:
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == '};'), None)
    if end is not None:
        key_re = re.compile(r'^\s*([\'\"])(.*?)\1\s*:')
        last_index = {}
        for i in range(start + 1, end):
            m = key_re.match(lines[i])
            if m:
                last_index[m.group(2)] = i
        deduped = []
        removed = []
        for i, line in enumerate(lines):
            if start < i < end:
                m = key_re.match(line)
                if m and last_index.get(m.group(2)) != i:
                    removed.append(m.group(2))
                    continue
            deduped.append(line)
        lines = deduped
        s = '\n'.join(lines) + '\n'
        if removed:
            print('Removed duplicate RO keys:', ', '.join(sorted(set(removed))))

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
