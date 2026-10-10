from pathlib import Path

root = Path('passenger/lib/screens')

replacements = {
    'quote_screen.dart': [
        (
            'final initial=pickup??const LatLng(51.5074,-0.1278);',
            'final initial=pickup??dropoff??(routePoints.isNotEmpty?routePoints.first:null);',
        ),
        (
            'Positioned.fill(child:FlutterMap(',
            'Positioned.fill(child:initial==null ? const Center(child:CircularProgressIndicator()) : FlutterMap(',
        ),
    ],
    'trip_screen.dart': [
        (
            'final center = driverPoint ?? pickup ?? const LatLng(51.5074, -0.1278);',
            'final center = driverPoint ?? pickup ?? dropoff;',
        ),
        (
            'child: FlutterMap(\n                  mapController: map,',
            'child: center == null ? const Center(child: CircularProgressIndicator()) : FlutterMap(\n                  mapController: map,',
        ),
    ],
    'delivery_screen.dart': [
        (
            'final center = driverPoint ?? (points.isNotEmpty ? points.first : const LatLng(51.5074, -0.1278));',
            'final center = driverPoint ?? (points.isNotEmpty ? points.first : null);',
        ),
        (
            'child: FlutterMap(\n                  mapController: map,',
            'child: center == null ? const Center(child: CircularProgressIndicator()) : FlutterMap(\n                  mapController: map,',
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

# Do not ship stale backup Dart files containing obsolete fallback coordinates.
for backup in root.glob('*.orig'):
    backup.unlink()
