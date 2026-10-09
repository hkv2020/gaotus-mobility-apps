from pathlib import Path

root = Path('driver')

def replace(rel, old, new, label):
    p = root / rel
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'{label}: marker missing in {rel}')
    p.write_text(s.replace(old, new, 1))

replace('pubspec.yaml', 'version: 0.6.5+20', 'version: 0.6.6+21', 'pubspec version')
replace('lib/config/app_config.dart', "static const String version = '0.6.5';", "static const String version = '0.6.6';", 'app version')

# Firebase Messaging and /push/register already exist; this release activates them
# against the dedicated Gaotus Mobility Firebase Android project.
checks = {
    'pubspec.yaml': ['firebase_core:', 'firebase_messaging:', 'flutter_local_notifications:', 'version: 0.6.6+21'],
    'lib/services/push_service.dart': ['Firebase.initializeApp()', 'FirebaseMessaging.instance.getToken()', 'onTokenRefresh'],
    'lib/core/api_client.dart': ["'/push/register'"],
    'lib/state/app_session.dart': ['registerPush', '_push.onToken'],
}
for rel, needles in checks.items():
    text = (root / rel).read_text()
    for needle in needles:
        if needle not in text:
            raise SystemExit(f'missing {needle} in {rel}')

print('Applied Driver v0.6.6 Firebase Mobility activation patch.')
