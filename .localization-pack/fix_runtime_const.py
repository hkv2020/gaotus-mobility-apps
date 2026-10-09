from pathlib import Path
import sys

if len(sys.argv) != 2 or sys.argv[1] not in {'driver', 'passenger'}:
    raise SystemExit('usage: fix_runtime_const.py driver|passenger')

name = sys.argv[1]
root = Path(name)

# Keep this deliberately narrow. Localized strings are runtime expressions, so only
# the known const UI ancestors containing `.tr` must become non-const. Do not strip
# `const` globally: const collection defaults and declarations are part of Dart syntax
# and business/state code must stay byte-behaviour compatible.
if name == 'driver':
    path = root / 'lib/screens/login_screen.dart'
    text = path.read_text()
    old = "decoration: const InputDecoration(\n                        labelText: 'Email or username'.tr,"
    new = "decoration: InputDecoration(\n                        labelText: 'Email or username'.tr,"
    if old not in text:
        raise SystemExit('Driver localized InputDecoration const target not found')
    path.write_text(text.replace(old, new, 1))
else:
    path = root / 'lib/screens/chat_screen.dart'
    text = path.read_text()
    old = "title: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[\n            Text('Your driver'.tr,"
    new = "title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[\n            Text('Your driver'.tr,"
    if old not in text:
        raise SystemExit('Passenger localized chat Column const target not found')
    path.write_text(text.replace(old, new, 1))

print(f'Applied narrow runtime localization const fix for {name}')
