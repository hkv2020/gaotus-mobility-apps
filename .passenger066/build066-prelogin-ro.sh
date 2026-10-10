#!/usr/bin/env bash
set -euo pipefail

# Reconstruct the exact known-good Passenger v0.6.5 Firebase RO baseline.
bash .passenger065/build065-firebase-ro.sh

sha256sum \
  passenger/lib/services/push_service.dart \
  passenger/lib/services/passenger_notification_service.dart \
  passenger/lib/services/realtime_service.dart \
  passenger/android/app/google-services.json \
  > /tmp/passenger066-critical.before

# Apply only the pre-login Country Pack/localization delta.
patch -p2 -d passenger < .passenger066/prelogin-localization.patch

sha256sum \
  passenger/lib/services/push_service.dart \
  passenger/lib/services/passenger_notification_service.dart \
  passenger/lib/services/realtime_service.dart \
  passenger/android/app/google-services.json \
  > /tmp/passenger066-critical.after
diff -u /tmp/passenger066-critical.before /tmp/passenger066-critical.after

grep -q 'version: 0.6.6+27' passenger/pubspec.yaml
grep -q "static const version = '0.6.6'" passenger/lib/config/app_config.dart
grep -q 'refreshPublicCountry' passenger/lib/state/passenger_session.dart
grep -q 'gmp_passenger_country' passenger/lib/core/secure_store.dart
grep -q "'Invalid credentials.': 'Date de autentificare incorecte.'" passenger/lib/core/localization.dart
grep -q 'com.gaotus.gaotus_mobility_passenger' passenger/android/app/google-services.json

python3 - <<'PY'
from pathlib import Path
p=Path('passenger/GAOTUS-MOBILITY-PASSENGER-v0.6.6-PRELOGIN-LOCALIZATION-QA.md')
s=p.read_text()
s=s.replace('- Flutter SDK is not available in the current execution environment, so `flutter analyze` and release APK rebuild were not run here.', '- GitHub Actions rebuild runs `flutter analyze --no-fatal-infos` and `flutter build apk --release` before packaging.')
p.write_text(s)
PY

cd passenger
flutter pub get
flutter analyze --no-fatal-infos
flutter build apk --release
cd ..

rm -f Gaotus-Mobility-Passenger-v0.6.6-PRELOGIN-RO.apk \
      Gaotus-Mobility-Passenger-v0.6.6-PRELOGIN-RO-SOURCE.zip \
      SHA256SUMS-PASSENGER-V066.txt
cp passenger/build/app/outputs/flutter-apk/app-release.apk Gaotus-Mobility-Passenger-v0.6.6-PRELOGIN-RO.apk
zip -qr Gaotus-Mobility-Passenger-v0.6.6-PRELOGIN-RO-SOURCE.zip passenger \
  -x 'passenger/build/*' 'passenger/.dart_tool/*' 'passenger/android/.gradle/*' 'passenger/.idea/*'
sha256sum \
  Gaotus-Mobility-Passenger-v0.6.6-PRELOGIN-RO.apk \
  Gaotus-Mobility-Passenger-v0.6.6-PRELOGIN-RO-SOURCE.zip \
  | tee SHA256SUMS-PASSENGER-V066.txt
