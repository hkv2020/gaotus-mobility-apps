#!/usr/bin/env bash
set -euo pipefail

# Reconstruct exact known-good Driver v0.6.7 PRELOGIN-RO baseline.
bash .driver067/build067-prelogin-ro.sh

sha256sum \
  driver/lib/services/offer_notification_service.dart \
  driver/lib/services/push_service.dart \
  driver/lib/services/realtime_service.dart \
  driver/android/app/google-services.json \
  > /tmp/driver068-critical.before

# Apply only GPS-first map startup delta.
patch -p1 -d driver < .driver068/gps-first-map.patch

sha256sum \
  driver/lib/services/offer_notification_service.dart \
  driver/lib/services/push_service.dart \
  driver/lib/services/realtime_service.dart \
  driver/android/app/google-services.json \
  > /tmp/driver068-critical.after
diff -u /tmp/driver068-critical.before /tmp/driver068-critical.after

grep -q 'version: 0.6.8+23' driver/pubspec.yaml
grep -q "static const String version = '0.6.8'" driver/lib/config/app_config.dart
grep -q 'unawaited(widget.session.primeLocation())' driver/lib/screens/driver_home_screen.dart
! grep -q 'LatLng(51.5074, -0.1278)' driver/lib/screens/driver_home_screen.dart
grep -q 'ai.gaotus.gaotus_mobility_driver' driver/android/app/google-services.json

cd driver
flutter pub get
flutter analyze --no-fatal-infos
flutter build apk --release
cd ..

rm -f Gaotus-Mobility-Driver-v0.6.8-GPS-FIRST-MAP.apk \
      Gaotus-Mobility-Driver-v0.6.8-GPS-FIRST-MAP-SOURCE.zip \
      SHA256SUMS-DRIVER-V068.txt
cp driver/build/app/outputs/flutter-apk/app-release.apk Gaotus-Mobility-Driver-v0.6.8-GPS-FIRST-MAP.apk
zip -qr Gaotus-Mobility-Driver-v0.6.8-GPS-FIRST-MAP-SOURCE.zip driver \
  -x 'driver/build/*' 'driver/.dart_tool/*' 'driver/android/.gradle/*' 'driver/.idea/*'
sha256sum \
  Gaotus-Mobility-Driver-v0.6.8-GPS-FIRST-MAP.apk \
  Gaotus-Mobility-Driver-v0.6.8-GPS-FIRST-MAP-SOURCE.zip \
  | tee SHA256SUMS-DRIVER-V068.txt
