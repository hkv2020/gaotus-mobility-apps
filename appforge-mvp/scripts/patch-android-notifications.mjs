import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, out);
    else if (/MainActivity\.java$/.test(full)) out.push(full);
  }
  return out;
}

function ensureImport(src, value) {
  const statement = `import ${value};`;
  if (src.includes(statement)) return src;
  const packageMarker = src.match(/package\s+[\w.]+\s*;\s*\n/);
  if (!packageMarker) throw new Error(`Cannot insert Android import ${value}: package declaration missing`);
  return src.replace(packageMarker[0], `${packageMarker[0]}${statement}\n`);
}

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const n = client.notifications || {};
const provider = ['firebase', 'onesignal'].includes(n.provider) ? n.provider : 'none';
if (provider === 'none') {
  console.log('[AppForge] push notifications disabled');
  process.exit(0);
}

const encoded = String(client.firebaseGoogleServicesB64 || '');
if (!encoded) throw new Error(`${provider} push requires google-services.json in AppForge Notifications`);
let firebaseRaw;
try {
  firebaseRaw = Buffer.from(encoded, 'base64').toString('utf8');
  JSON.parse(firebaseRaw);
} catch {
  throw new Error('Invalid firebaseGoogleServicesB64 configuration');
}
const firebase = JSON.parse(firebaseRaw);
const packages = (firebase.client || []).map((x) => x?.client_info?.android_client_info?.package_name).filter(Boolean);
if (!packages.includes(client.appId)) throw new Error(`google-services.json does not match ${client.appId}`);

const appDir = path.join(rootDir, 'android', 'app');
fs.writeFileSync(path.join(appDir, 'google-services.json'), firebaseRaw + (firebaseRaw.endsWith('\n') ? '' : '\n'));

const gradlePath = path.join(appDir, 'build.gradle');
let gradle = fs.readFileSync(gradlePath, 'utf8');
const depMarker = `implementation project(':capacitor-cordova-android-plugins')`;
if (!gradle.includes(depMarker)) throw new Error('Capacitor dependency marker not found in app/build.gradle');
let deps = `\n    implementation 'com.google.firebase:firebase-messaging:25.0.1'`;
if (provider === 'onesignal') {
  if (!String(n.onesignal_app_id || '').trim()) throw new Error('OneSignal provider requires OneSignal App ID');
  deps += `\n    implementation 'com.onesignal:OneSignal:5.1.37'`;
}
if (!gradle.includes('com.google.firebase:firebase-messaging')) gradle = gradle.replace(depMarker, depMarker + deps);
else if (provider === 'onesignal' && !gradle.includes('com.onesignal:OneSignal')) gradle = gradle.replace(depMarker, depMarker + `\n    implementation 'com.onesignal:OneSignal:5.1.37'`);
fs.writeFileSync(gradlePath, gradle);

const mains = walk(path.join(appDir, 'src', 'main', 'java'));
if (mains.length !== 1) throw new Error(`Expected one MainActivity.java, found ${mains.length}`);
const mainPath = mains[0];
let main = fs.readFileSync(mainPath, 'utf8');
const pkg = (main.match(/package\s+([\w.]+)\s*;/) || [])[1] || client.appId;

// Never depend on another patcher's import layout. Each required push import is reconciled independently.
for (const required of [
  'android.Manifest',
  'android.content.pm.PackageManager',
  'android.os.Build',
]) main = ensureImport(main, required);

const ask = n.ask_permission_on_launch !== false;
let init = '';
if (provider === 'onesignal') {
  main = ensureImport(main, 'com.onesignal.OneSignal');
  main = ensureImport(main, 'com.onesignal.Continue');
  init += `\n    OneSignal.initWithContext(getApplicationContext(), ${JSON.stringify(String(n.onesignal_app_id))});`;
  if (ask) init += `\n    OneSignal.getNotifications().requestPermission(false, Continue.none());`;
}
if (ask) {
  init += `\n    if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {\n      requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 7601);\n    }`;
}
if (init && !main.includes('APPFORGE_PUSH_INITIALIZED')) {
  const marker = '    super.onCreate(savedInstanceState);';
  if (!main.includes(marker)) throw new Error('MainActivity onCreate marker missing for push initialization');
  main = main.replace(marker, `${marker}\n    // APPFORGE_PUSH_INITIALIZED${init}`);
}
fs.writeFileSync(mainPath, main);

const manifestPath = path.join(appDir, 'src', 'main', 'AndroidManifest.xml');
let manifest = fs.readFileSync(manifestPath, 'utf8');
if (!manifest.includes('android.permission.POST_NOTIFICATIONS')) manifest = manifest.replace('<application', '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n\n    <application');

const serviceClass = `${pkg}.GaotusFirebaseMessagingService`;
if (!manifest.includes(serviceClass)) {
  manifest = manifest.replace('</application>', `        <service\n            android:name=".GaotusFirebaseMessagingService"\n            android:exported="false">\n            <intent-filter>\n                <action android:name="com.google.firebase.MESSAGING_EVENT" />\n            </intent-filter>\n        </service>\n    </application>`);
}
fs.writeFileSync(manifestPath, manifest);

const service = `package ${pkg};\n\nimport android.app.NotificationChannel;\nimport android.app.NotificationManager;\nimport android.content.Context;\nimport android.os.Build;\nimport android.util.Log;\nimport androidx.core.app.NotificationCompat;\nimport androidx.core.app.NotificationManagerCompat;\nimport com.google.firebase.messaging.FirebaseMessagingService;\nimport com.google.firebase.messaging.RemoteMessage;\n\npublic class GaotusFirebaseMessagingService extends FirebaseMessagingService {\n  private static final String CHANNEL = "gaotus_appforge_push";\n\n  @Override\n  public void onNewToken(String token) {\n    super.onNewToken(token);\n    Log.i("AppForgePush", "FCM token refreshed");\n  }\n\n  @Override\n  public void onMessageReceived(RemoteMessage message) {\n    super.onMessageReceived(message);\n    ${n.disable_foreground === true ? 'return;' : `String title = "${String(client.appName).replace(/\\/g,'\\\\').replace(/"/g,'\\"')}";\n    String body = "New notification";\n    if (message.getNotification() != null) {\n      if (message.getNotification().getTitle() != null) title = message.getNotification().getTitle();\n      if (message.getNotification().getBody() != null) body = message.getNotification().getBody();\n    } else if (message.getData() != null) {\n      if (message.getData().get("title") != null) title = message.getData().get("title");\n      if (message.getData().get("body") != null) body = message.getData().get("body");\n    }\n    ensureChannel();\n    NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL)\n      .setSmallIcon(getApplicationInfo().icon)\n      .setContentTitle(title)\n      .setContentText(body)\n      .setAutoCancel(true)\n      .setPriority(NotificationCompat.PRIORITY_DEFAULT);\n    try { NotificationManagerCompat.from(this).notify((int)(System.currentTimeMillis() & 0x7fffffff), builder.build()); } catch (SecurityException ignored) {}` }\n  }\n\n  private void ensureChannel() {\n    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {\n      NotificationChannel channel = new NotificationChannel(CHANNEL, "App notifications", NotificationManager.IMPORTANCE_DEFAULT);\n      NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);\n      if (manager != null) manager.createNotificationChannel(channel);\n    }\n  }\n}\n`;
fs.writeFileSync(path.join(path.dirname(mainPath), 'GaotusFirebaseMessagingService.java'), service);

console.log(`[AppForge] ${provider} push runtime configured for ${client.appId}; required imports reconciled`);
