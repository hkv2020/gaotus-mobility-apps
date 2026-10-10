from pathlib import Path

root = Path('driver/lib/screens')

replacements = {
    'operations_job_screen.dart': [
        (
            """final center = next?.lat != null && next?.lng != null
            ? LatLng(next!.lat!, next.lng!)
            : points.isNotEmpty
                ? points.first
                : const LatLng(51.5074, -0.1278);""",
            """final center = next?.lat != null && next?.lng != null
            ? LatLng(next!.lat!, next.lng!)
            : points.isNotEmpty
                ? points.first
                : null;""",
        ),
        (
            'child: FlutterMap(\n                  options: MapOptions(',
            'child: center == null ? const Center(child: CircularProgressIndicator()) : FlutterMap(\n                  options: MapOptions(',
        ),
    ],
    'job_screen.dart': [
        (
            'final center = points.isNotEmpty ? points.first : const LatLng(51.5074, -0.1278);',
            'final center = points.isNotEmpty ? points.first : null;',
        ),
        (
            'child: FlutterMap(\n                  options: MapOptions(',
            'child: center == null ? const Center(child: CircularProgressIndicator()) : FlutterMap(\n                  options: MapOptions(',
        ),
    ],
}

for filename, pairs in replacements.items():
    path = root / filename
    text = path.read_text()
    for old, new in pairs:
        if old not in text:
            raise SystemExit(f'Expected map fallback pattern missing in {filename}: {old!r}')
        text = text.replace(old, new, 1)
    path.write_text(text)

for backup in root.glob('*.orig'):
    backup.unlink()
