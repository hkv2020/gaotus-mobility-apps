from pathlib import Path
import sys

if len(sys.argv) != 2 or sys.argv[1] not in {'driver', 'passenger'}:
    raise SystemExit('usage: fix_runtime_const.py driver|passenger')

root = Path(sys.argv[1])
for base in ('screens', 'widgets', 'state'):
    folder = root / 'lib' / base
    if not folder.exists():
        continue
    for path in folder.glob('*.dart'):
        text = path.read_text()
        if '.tr' not in text:
            continue
        # Localized values are runtime expressions. A const ancestor anywhere in the
        # same widget/expression can make Dart reject an otherwise valid `.tr` value.
        # Removing const in localization-touched UI files changes no business logic;
        # it only forfeits compile-time widget canonicalization in those files.
        path.write_text(text.replace('const ', ''))
print(f'Normalized runtime localization const expressions for {sys.argv[1]}')
