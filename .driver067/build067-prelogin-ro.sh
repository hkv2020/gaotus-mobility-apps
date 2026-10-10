#!/usr/bin/env bash
set -euo pipefail

# Reconstruct the exact known-good Driver v0.6.6 Firebase RO baseline.
bash .driver066/build066-firebase-ro.sh

sha256sum \
  driver/lib/services/offer_notification_service.dart \
  driver/lib/services/push_service.dart \
  driver/lib/services/realtime_service.dart \
  driver/android/app/google-services.json \
  > /tmp/driver067-critical.before

# Apply only the pre-login Country Pack/localization delta.
patch -p2 -d driver < .driver067/prelogin-localization.patch

sha256sum \
  driver/lib/services/offer_notification_service.dart \
  driver/lib/services/push_service.dart \
  driver/lib/services/realtime_service.dart \
  driver/android/app/google-services.json \
  > /tmp/driver067-critical.after
diff -u /tmp/driver067-critical.before /tmp/driver067-critical.after

grep -q 'version: 0.6.7+22' driver/pubspec.yaml
grep -q "static const String version = '0.6.7'" driver/lib/config/app_config.dart
grep -q 'refreshPublicCountry' driver/lib/state/app_session.dart
grep -q 'gmp_country_config' driver/lib/core/secure_store.dart
grep -q "'Contacting server…': 'Contactăm serverul…'" driver/lib/core/localization.dart
grep -q 'ai.gaotus.gaotus_mobility_driver' driver/android/app/google-services.json

python3 - <<'PY'
from pathlib import Path
p=Path('driver/GAOTUS-MOBILITY-DRIVER-v0.6.7-PRELOGIN-LOCALIZATION-QA.md')
s=p.read_text()
s=s.replace('- Flutter SDK is not available in the current execution environment, so `flutter analyze` and release APK rebuild were not run here.', '- GitHub Actions rebuild runs `flutter analyze --no-fatal-infos` and `flutter build apk --release` before packaging.')
p.write_text(s)
PY

cd driver
flutter pub get
flutter analyze --no-fatal-infos
flutter build apk --release
cd ..

rm -f Gaotus-Mobility-Driver-v0.6.7-PRELOGIN-RO.apk \
      Gaotus-Mobility-Driver-v0.6.7-PRELOGIN-RO-SOURCE.zip \
      SHA256SUMS-DRIVER-V067.txt
cp driver/build/app/outputs/flutter-apk/app-release.apk Gaotus-Mobility-Driver-v0.6.7-PRELOGIN-RO.apk
zip -qr Gaotus-Mobility-Driver-v0.6.7-PRELOGIN-RO-SOURCE.zip driver \
  -x 'driver/build/*' 'driver/.dart_tool/*' 'driver/android/.gradle/*' 'driver/.idea/*'
sha256sum \
  Gaotus-Mobility-Driver-v0.6.7-PRELOGIN-RO.apk \
  Gaotus-Mobility-Driver-v0.6.7-PRELOGIN-RO-SOURCE.zip \
  | tee SHA256SUMS-DRIVER-V067.txt
