from pathlib import Path

root=Path('driver')

def replace_one(path, old, new, label):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise SystemExit(f'{label} marker missing in {path}')
    p.write_text(s.replace(old,new,1))

replace_one('pubspec.yaml','version: 0.5.4+9','version: 0.5.5+10','version')
replace_one('lib/config/app_config.dart',"static const String version = '0.5.4';","static const String version = '0.5.5';",'app version')

p=root/'lib/screens/driver_home_screen.dart'
s=p.read_text()
s=s.replace("        width: 68,","        width: 56,",1)
s=s.replace("        height: 72,","        height: 60,",1)
s=s.replace("          size: 56,","          size: 44,",1)
p.write_text(s)

checks={
  'pubspec.yaml':['version: 0.5.5+10'],
  'lib/config/app_config.dart':["version = '0.5.5'"],
  'lib/screens/driver_home_screen.dart':['width: 56','height: 60','size: 44'],
}
for path,needles in checks.items():
    text=(root/path).read_text()
    for needle in needles:
        if needle not in text: raise SystemExit(f'missing {needle} in {path}')
print('Driver v0.5.5 smaller premium car marker applied')
