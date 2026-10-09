from pathlib import Path

root = Path('passenger')

def replace(rel, old, new, label):
    p = root / rel
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'{label}: marker missing in {rel}')
    p.write_text(s.replace(old, new, 1))

replace('pubspec.yaml', 'version: 0.6.4+25', 'version: 0.6.5+26', 'pubspec version')
replace('lib/config/app_config.dart', "static const version = '0.6.4';", "static const version = '0.6.5';", 'app version')

# The Firebase runtime and /push/register contract already exist in the canonical app.
# This release intentionally only activates them with the real Mobility Firebase Android config.
checks = {
    'pubspec.yaml': ['firebase_core:', 'firebase_messaging:', 'flutter_local_notifications:', 'version: 0.6.5+26'],
    'lib/services/push_service.dart': ['Firebase.initializeApp()', 'FirebaseMessaging.instance.getToken()', 'onTokenRefresh'],
    'lib/core/api_client.dart': ["'/push/register'"],
    'lib/state/passenger_session.dart': ['_registerPush()', '_push.onToken'],
}
for rel, needles in checks.items():
    text = (root / rel).read_text()
    for needle in needles:
        if needle not in text:
            raise SystemExit(f'missing {needle} in {rel}')

print('Applied Passenger v0.6.5 Firebase Mobility activation patch.')
