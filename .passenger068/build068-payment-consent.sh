#!/usr/bin/env bash
set -euo pipefail

# Reconstruct exact known-good Passenger v0.6.7+28 GPS-FIRST-MAP baseline.
bash .passenger067/build067-gps-first-map.sh

sha256sum \
  passenger/lib/services/push_service.dart \
  passenger/lib/services/passenger_notification_service.dart \
  passenger/lib/services/realtime_service.dart \
  passenger/lib/services/location_service.dart \
  passenger/lib/screens/home_screen.dart \
  passenger/android/app/google-services.json \
  > /tmp/passenger068-critical.before

patch -p1 -d passenger < .passenger068/payment-consent.patch

sha256sum \
  passenger/lib/services/push_service.dart \
  passenger/lib/services/passenger_notification_service.dart \
  passenger/lib/services/realtime_service.dart \
  passenger/lib/services/location_service.dart \
  passenger/lib/screens/home_screen.dart \
  passenger/android/app/google-services.json \
  > /tmp/passenger068-critical.after
diff -u /tmp/passenger068-critical.before /tmp/passenger068-critical.after

grep -q 'version: 0.6.8+29' passenger/pubspec.yaml
grep -q "static const version = '0.6.8'" passenger/lib/config/app_config.dart
grep -q "extras_autocharge_consent" passenger/lib/state/passenger_session.dart
grep -q "extrasAutochargeConsent=false" passenger/lib/screens/quote_screen.dart
grep -q "Allow verified trip extras to be charged automatically" passenger/lib/core/localization.dart
! grep -R -q 'LatLng(51.5074, -0.1278)' passenger/lib --include='*.dart'
grep -q 'com.gaotus.gaotus_mobility_passenger' passenger/android/app/google-services.json

cd passenger
flutter pub get
flutter analyze --no-fatal-infos
flutter build apk --release
cd ..

rm -f Gaotus-Mobility-Passenger-v0.6.8-PAYMENT-CONSENT.apk \
      Gaotus-Mobility-Passenger-v0.6.8-PAYMENT-CONSENT-SOURCE.zip \
      SHA256SUMS-PASSENGER-V068.txt
cp passenger/build/app/outputs/flutter-apk/app-release.apk Gaotus-Mobility-Passenger-v0.6.8-PAYMENT-CONSENT.apk
zip -qr Gaotus-Mobility-Passenger-v0.6.8-PAYMENT-CONSENT-SOURCE.zip passenger \
  -x 'passenger/build/*' 'passenger/.dart_tool/*' 'passenger/android/.gradle/*' 'passenger/.idea/*'
sha256sum \
  Gaotus-Mobility-Passenger-v0.6.8-PAYMENT-CONSENT.apk \
  Gaotus-Mobility-Passenger-v0.6.8-PAYMENT-CONSENT-SOURCE.zip \
  | tee SHA256SUMS-PASSENGER-V068.txt
