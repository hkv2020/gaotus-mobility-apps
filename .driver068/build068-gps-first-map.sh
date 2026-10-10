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

# Apply GPS-first startup delta, then remove every remaining active London map fallback.
patch -p1 -d driver < .driver068/gps-first-map.patch
python3 .map-cleanup/driver_global_map_cleanup.py

# The nullable branch has already narrowed center to LatLng in the map branch.
# Remove the redundant non-null assertion so flutter analyze stays warning-clean
# for this delta without changing runtime behavior.
python3 - <<'PY'
from pathlib import Path
p=Path('driver/lib/screens/driver_home_screen.dart')
s=p.read_text().replace(
    'options: MapOptions(initialCenter: center!, initialZoom: 15.2),',
    'options: MapOptions(initialCenter: center, initialZoom: 15.2),',
)
p.write_text(s)
PY

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
! grep -R -q --include='*.dart' -E '51\.5074|-0\.1278' driver/lib
! grep -q 'initialCenter: center!' driver/lib/screens/driver_home_screen.dart
grep -q 'center == null ? const Center' driver/lib/screens/job_screen.dart
grep -q 'center == null ? const Center' driver/lib/screens/operations_job_screen.dart
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
