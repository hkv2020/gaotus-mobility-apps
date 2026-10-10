#!/usr/bin/env bash
set -euo pipefail

# Reconstruct exact known-good Passenger v0.6.6 PRELOGIN-RO baseline.
bash .passenger066/build066-prelogin-ro.sh

sha256sum \
  passenger/lib/services/push_service.dart \
  passenger/lib/services/passenger_notification_service.dart \
  passenger/lib/services/realtime_service.dart \
  passenger/android/app/google-services.json \
  > /tmp/passenger067-critical.before

# Apply GPS-first startup delta, then remove every remaining active London map fallback.
patch -p1 -d passenger < .passenger067/gps-first-map.patch
python3 .map-cleanup/passenger_global_map_cleanup.py

# v0.6.6 already contains this translation from the Romanian sweep. Keep the
# baseline translation and remove only the duplicate line introduced by the
# GPS-first patch so the const localization map stays valid.
python3 - <<'PY'
from pathlib import Path
p=Path('passenger/lib/core/localization.dart')
s=p.read_text()
s=s.replace('    "Finding your location…": "Îți găsim locația…",\n', '', 1)
p.write_text(s)
PY

sha256sum \
  passenger/lib/services/push_service.dart \
  passenger/lib/services/passenger_notification_service.dart \
  passenger/lib/services/realtime_service.dart \
  passenger/android/app/google-services.json \
  > /tmp/passenger067-critical.after
diff -u /tmp/passenger067-critical.before /tmp/passenger067-critical.after

grep -q 'version: 0.6.7+28' passenger/pubspec.yaml
grep -q "static const version = '0.6.7'" passenger/lib/config/app_config.dart
grep -q 'Future<Position?> lastKnown()' passenger/lib/services/location_service.dart
grep -q "Finding your location…" passenger/lib/core/localization.dart
! grep -R -q --include='*.dart' -E '51\.5074|-0\.1278' passenger/lib
grep -q 'initial==null ? const Center' passenger/lib/screens/quote_screen.dart
grep -q 'center == null ? const Center' passenger/lib/screens/trip_screen.dart
grep -q 'center == null ? const Center' passenger/lib/screens/delivery_screen.dart
grep -q 'com.gaotus.gaotus_mobility_passenger' passenger/android/app/google-services.json

cd passenger
flutter pub get
flutter analyze --no-fatal-infos
flutter build apk --release
cd ..

rm -f Gaotus-Mobility-Passenger-v0.6.7-GPS-FIRST-MAP.apk \
      Gaotus-Mobility-Passenger-v0.6.7-GPS-FIRST-MAP-SOURCE.zip \
      SHA256SUMS-PASSENGER-V067.txt
cp passenger/build/app/outputs/flutter-apk/app-release.apk Gaotus-Mobility-Passenger-v0.6.7-GPS-FIRST-MAP.apk
zip -qr Gaotus-Mobility-Passenger-v0.6.7-GPS-FIRST-MAP-SOURCE.zip passenger \
  -x 'passenger/build/*' 'passenger/.dart_tool/*' 'passenger/android/.gradle/*' 'passenger/.idea/*'
sha256sum \
  Gaotus-Mobility-Passenger-v0.6.7-GPS-FIRST-MAP.apk \
  Gaotus-Mobility-Passenger-v0.6.7-GPS-FIRST-MAP-SOURCE.zip \
  | tee SHA256SUMS-PASSENGER-V067.txt
