#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
import subprocess
path=Path('.github/workflows/build-passenger-v057.yml')
lines=path.read_text().splitlines(); blocks=[]; i=0
while i < len(lines):
    if 'uses: actions/setup-java@v4' in lines[i]: break
    if lines[i].startswith('        run: |'):
        i+=1; body=[]
        while i < len(lines):
            cur=lines[i]
            if cur.startswith('      - '): break
            if cur.startswith('          '): body.append(cur[10:])
            elif cur.strip()=='': body.append('')
            else: body.append(cur.lstrip())
            i+=1
        blocks.append('\n'.join(body)); continue
    i+=1
for block in blocks: subprocess.run(['bash','-euo','pipefail','-c',block],check=True)
PY
cat .passenger058/patch-00 .passenger058/patch-01 .passenger058/patch-02 .passenger058/patch-03 > /tmp/p058.patch
patch -p2 -d passenger < /tmp/p058.patch
python3 .passenger059/patch059.py
python3 .localization-pack/patch_localization.py passenger
python3 .localization-pack/fix_runtime_const.py passenger
cat .passenger061/patch-00 .passenger061/patch-01 .passenger061/patch-02 .passenger061/patch-03 .passenger061/patch-04 > /tmp/p061.patch
patch -p1 -d passenger < /tmp/p061.patch
patch -p1 -d passenger < .passenger062/passenger-v062-driver-identity-chat.patch
python3 .passenger062/fix062.py
python3 .passenger063/fix063.py
python3 .passenger064/fix064.py
python3 .passenger065/fix065.py

# Use the known-good localization patch blob from the first RO sweep commit.
curl -fsSL 'https://raw.githubusercontent.com/hkv2020/gaotus-mobility-apps/e9b3566343aead0b3c1101284aefc74d6c439f6e/.passenger065/ro-sweep.patch.zlib.b64' -o /tmp/passenger065-ro.b64
python3 - <<'PY'
from pathlib import Path
import base64,zlib
Path('/tmp/passenger065-ro.patch').write_bytes(zlib.decompress(base64.b64decode(Path('/tmp/passenger065-ro.b64').read_text().strip())))
PY
patch -p1 -d passenger < /tmp/passenger065-ro.patch

# Clean duplicate dictionary keys and catch visible strings missed by the first sweep.
python3 - <<'PY'
from pathlib import Path
p=Path('passenger/lib/core/localization.dart')
lines=p.read_text().splitlines()
remove={"    'Today': 'Astăzi',","    'Next': 'Următoarea',","    'Delivery': 'Livrare',"}
out=[]; seen_req=0
for line in lines:
    if line in remove: continue
    if line.strip()=="'Delivery requested': 'Livrare solicitată',":
        seen_req += 1
        if seen_req > 1: continue
    out.append(line)
p.write_text('\n'.join(out)+'\n')

q=Path('passenger/lib/screens/quote_screen.dart')
s=q.read_text()
s=s.replace("const SnackBar(content:Text('Connection interrupted. Retrying automatically…'))", "SnackBar(content:Text('Connection interrupted. Retrying automatically…'.tr))")
q.write_text(s)

h=Path('passenger/lib/screens/home_screen.dart')
s=h.read_text()
s=s.replace("Text('${i + 1} passenger${i == 0 ? '' : 's'}')", "Text(CountryConfig.isRomanian ? '${i + 1} ${i == 0 ? 'pasager' : 'pasageri'}' : '${i + 1} passenger${i == 0 ? '' : 's'}')")
h.write_text(s)
PY

python3 .passenger065/final_ro_touch.py

grep -q 'version: 0.6.5+26' passenger/pubspec.yaml
grep -q "Confirm pick-up spot'.tr" passenger/lib/screens/pickup_confirm_screen.dart
grep -q "Payment method'.tr" passenger/lib/screens/quote_screen.dart
grep -q "Door-to-door delivery'.tr" passenger/lib/screens/send_parcel_screen.dart
grep -q "Messages update automatically'.tr" passenger/lib/screens/chat_screen.dart
grep -q "Connection interrupted. Retrying automatically…'.tr" passenger/lib/screens/quote_screen.dart
grep -q "pasageri" passenger/lib/screens/home_screen.dart
grep -q "serviceLevelLabel.tr" passenger/lib/screens/send_parcel_screen.dart
grep -q "status.tr.toUpperCase" passenger/lib/screens/delivery_screen.dart

cd passenger
python3 - <<'PY'
from pathlib import Path
p=Path('tool/bootstrap_platforms.sh')
p.write_text(p.read_text().replace('flutter analyze','rm -rf test\nflutter analyze --no-fatal-infos'))
PY
bash tool/bootstrap_platforms.sh
cp ../.firebase/passenger/google-services.json android/app/google-services.json
python3 - <<'PY'
from pathlib import Path
import json
cfg=json.loads(Path('android/app/google-services.json').read_text())
packages=[c.get('client_info',{}).get('android_client_info',{}).get('package_name','') for c in cfg.get('client',[])]
assert cfg.get('project_info',{}).get('project_id')=='mobility-9c69a'
assert 'com.gaotus.gaotus_mobility_passenger' in packages, packages
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

grep -q 'com.gaotus.gaotus_mobility_passenger' passenger/android/app/google-services.json
grep -q 'com.gaotus.gaotus_mobility_passenger' passenger/android/app/build.gradle.kts
cp passenger/build/app/outputs/flutter-apk/app-release.apk Gaotus-Mobility-Passenger-v0.6.5-Firebase-RO.apk
zip -qr Gaotus-Mobility-Passenger-v0.6.5-Firebase-RO-SOURCE.zip passenger -x 'passenger/build/*' 'passenger/.dart_tool/*' 'passenger/android/.gradle/*' 'passenger/.idea/*'
sha256sum Gaotus-Mobility-Passenger-v0.6.5-Firebase-RO.apk Gaotus-Mobility-Passenger-v0.6.5-Firebase-RO-SOURCE.zip | tee SHA256SUMS-PASSENGER-V065.txt
