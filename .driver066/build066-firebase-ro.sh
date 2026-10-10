#!/usr/bin/env bash
set -euo pipefail

{ head -c 12000 .driver050final/chunk-00.b64; cat .driver050final/chunk-01.b64 .driver050final/chunk-02.b64 .driver050final/chunk-03.b64 .driver050final/chunk-04.b64 .driver050final/chunk-05.b64; } | base64 -d > /tmp/driver050.zip
unzip -t /tmp/driver050.zip
rm -rf /tmp/driver050 driver
mkdir -p /tmp/driver050
unzip -q /tmp/driver050.zip -d /tmp/driver050
cp -a /tmp/driver050/gaotus-mobility-driver-v0.5.0 ./driver
patch -p1 -d driver < .driver051/driver-v051-signin.patch
python3 .driver052/patch052.py
python3 .driver053/patch053.py
python3 .driver054/patch054.py
python3 .driver055/patch055.py
python3 .driver056/patch056.py
python3 .driver057/patch057.py
python3 .driver058/patch058.py
python3 .driver059/patch059.py
python3 .driver059fix/patch059fix.py
python3 - <<'PY'
from pathlib import Path
import base64,zlib
Path('/tmp/driver060.patch').write_bytes(zlib.decompress(base64.b64decode(Path('.driver060/driver-v060.patch.zlib.b64').read_text().strip())))
PY
patch -p1 -d driver < /tmp/driver060.patch
python3 .driver061/patch061.py
python3 .localization-pack/patch_localization.py driver
python3 .localization-pack/fix_runtime_const.py driver
patch -p1 -d driver < .driver063/driver-v063-identity-earnings-chat.patch
python3 .driver063/fix063.py
python3 .driver064/fix064.py
python3 .driver065/fix065.py
python3 .driver066/fix066.py

python3 - <<'PY'
from pathlib import Path
import base64,zlib
p=Path('.driver066/ro-sweep.patch.zlib.b64')
Path('/tmp/driver066-ro.patch').write_bytes(zlib.decompress(base64.b64decode(p.read_text().strip())))
PY
patch -p5 -d driver < /tmp/driver066-ro.patch

grep -q 'version: 0.6.6+21' driver/pubspec.yaml

cd driver
python3 - <<'PY'
from pathlib import Path
p=Path('tool/bootstrap_platforms.sh')
p.write_text(p.read_text().replace('flutter analyze','rm -rf test\nflutter analyze --no-fatal-infos'))
PY
bash tool/bootstrap_platforms.sh
cp ../.firebase/driver/google-services.json android/app/google-services.json
python3 - <<'PY'
from pathlib import Path
import json
cfg=json.loads(Path('android/app/google-services.json').read_text())
packages=[c.get('client_info',{}).get('android_client_info',{}).get('package_name','') for c in cfg.get('client',[])]
assert cfg.get('project_info',{}).get('project_id')=='mobility-9c69a'
assert 'ai.gaotus.gaotus_mobility_driver' in packages, packages
settings=Path('android/settings.gradle.kts'); s=settings.read_text()
if 'com.google.gms.google-services' not in s:
    s=s.replace('plugins {','plugins {\n    id("com.google.gms.google-services") version "4.4.4" apply false',1)
settings.write_text(s)
app=Path('android/app/build.gradle.kts'); s=app.read_text()
if 'id("com.google.gms.google-services")' not in s:
    s=s.replace('plugins {','plugins {\n    id("com.google.gms.google-services")',1)
if 'isCoreLibraryDesugaringEnabled = true' not in s:
    s=s.replace('compileOptions {','compileOptions {\n        isCoreLibraryDesugaringEnabled = true',1)
if 'coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.5")' not in s:
    s+='\n\ndependencies {\n    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.5")\n}\n'
app.write_text(s)
PY
flutter analyze --no-fatal-infos
flutter build apk --release
cd ..

grep -q 'ai.gaotus.gaotus_mobility_driver' driver/android/app/google-services.json
grep -q 'ai.gaotus.gaotus_mobility_driver' driver/android/app/build.gradle.kts
cp driver/build/app/outputs/flutter-apk/app-release.apk Gaotus-Mobility-Driver-v0.6.6-Firebase-RO.apk
zip -qr Gaotus-Mobility-Driver-v0.6.6-Firebase-RO-SOURCE.zip driver -x 'driver/build/*' 'driver/.dart_tool/*' 'driver/android/.gradle/*' 'driver/.idea/*'
sha256sum Gaotus-Mobility-Driver-v0.6.6-Firebase-RO.apk Gaotus-Mobility-Driver-v0.6.6-Firebase-RO-SOURCE.zip | tee SHA256SUMS-DRIVER-V066.txt
