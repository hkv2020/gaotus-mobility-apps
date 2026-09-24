from pathlib import Path
import base64

root=Path('driver')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.5+10','version: 0.5.6+11','version')
replace_one('lib/config/app_config.dart',"static const String version = '0.5.5';","static const String version = '0.5.6';",'app version')

asset=root/'assets/audio/gaotus_alert.mp3'
asset.parent.mkdir(parents=True,exist_ok=True)
asset.write_bytes(base64.b64decode(Path('.driver056/gaotus_alert.b64').read_text().strip()))

p=root/'pubspec.yaml'
s=p.read_text()
if 'assets/audio/gaotus_alert.mp3' not in s:
    s=s.replace('flutter:\n  uses-material-design: true\n','flutter:\n  uses-material-design: true\n  assets:\n    - assets/audio/gaotus_alert.mp3\n',1)
p.write_text(s)

p=root/'tool/bootstrap_platforms.sh'
s=p.read_text()
copy_line='mkdir -p android/app/src/main/res/raw\ncp assets/audio/gaotus_alert.mp3 android/app/src/main/res/raw/gaotus_alert.mp3\n'
if 'android/app/src/main/res/raw/gaotus_alert.mp3' not in s:
    s=s.replace('python3 tool/patch_platforms.py\n','python3 tool/patch_platforms.py\n'+copy_line,1)
p.write_text(s)

p=root/'lib/services/offer_notification_service.dart'
s=p.read_text()
old="""      playSound: true,
      enableVibration: true,
"""
new="""      playSound: true,
      sound: RawResourceAndroidNotificationSound('gaotus_alert'),
      enableVibration: true,
"""
if old not in s: raise SystemExit('driver offer sound marker missing')
s=s.replace(old,new,1)
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.6+11','assets/audio/gaotus_alert.mp3'],
  'lib/config/app_config.dart':["version = '0.5.6'"],
  'lib/services/offer_notification_service.dart':["RawResourceAndroidNotificationSound('gaotus_alert')"],
  'tool/bootstrap_platforms.sh':['android/app/src/main/res/raw/gaotus_alert.mp3'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
if asset.stat().st_size<4000: raise SystemExit('driver sound asset unexpectedly small')
print('Driver v0.5.6 custom alert sound applied')
