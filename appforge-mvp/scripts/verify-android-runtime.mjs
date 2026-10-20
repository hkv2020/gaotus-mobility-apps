import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient, featurePlan } from './lib.mjs';

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, out); else out.push(full);
  }
  return out;
}

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const plan = featurePlan(client);
const android = path.join(rootDir, 'android');
const app = path.join(android, 'app');
if (!fs.existsSync(app)) throw new Error('Android app directory missing');
const mainFiles = walk(path.join(app, 'src', 'main', 'java')).filter((f) => /MainActivity\.java$/.test(f));
if (mainFiles.length !== 1) throw new Error(`Expected one MainActivity.java, found ${mainFiles.length}`);
const main = fs.readFileSync(mainFiles[0], 'utf8');
const bridgeFiles = walk(path.join(app, 'src', 'main', 'java')).filter((f) => /GaotusNativeBridge\.java$/.test(f));
if (bridgeFiles.length !== 1) throw new Error(`Expected one GaotusNativeBridge.java, found ${bridgeFiles.length}`);
const bridge = fs.readFileSync(bridgeFiles[0], 'utf8');
const manifest = fs.readFileSync(path.join(app, 'src', 'main', 'AndroidManifest.xml'), 'utf8');
const gradle = fs.readFileSync(path.join(app, 'build.gradle'), 'utf8');
const errors = [];
const expect = (condition, message) => { if (!condition) errors.push(message); };
const hasPermission = (name) => manifest.includes(`android:name="${name}"`) || manifest.includes(`android:name='${name}'`);

expect(main.includes(`package ${client.appId};`), 'MainActivity package does not match appId');
expect(main.includes(`APPFORGE_START_URL = ${JSON.stringify(String(client.url || ''))}`), 'MainActivity start URL does not match generated config');
expect(bridge.includes(`allowedHost = \"${plan.host}\"`), 'Native bridge allowed host does not match generated config');
expect(gradle.includes(`versionCode ${client.versionCode}`), 'Gradle versionCode mismatch');
expect(gradle.includes(`versionName "${client.versionName}"`), 'Gradle versionName mismatch');
expect(fs.existsSync(path.join(rootDir, 'www', 'offline.html')), 'offline.html missing');
expect(fs.existsSync(path.join(rootDir, 'www', 'error.html')), 'error.html missing');

const configured = client.permissions || {};
const features = client.features || {};
const boolOr = (key, fallback) => typeof configured[key] === 'boolean' ? configured[key] : fallback;
const permissions = {
  camera: boolOr('camera', features.camera === true),
  location: boolOr('location', features.location === true),
  microphone: boolOr('microphone', false),
  vibration: boolOr('vibration', features.haptics === true),
};
expect(hasPermission('android.permission.CAMERA') === permissions.camera, 'CAMERA permission mismatch');
expect(hasPermission('android.permission.VIBRATE') === permissions.vibration, 'VIBRATE permission mismatch');
expect(hasPermission('android.permission.ACCESS_COARSE_LOCATION') === permissions.location, 'COARSE_LOCATION permission mismatch');
expect(hasPermission('android.permission.ACCESS_FINE_LOCATION') === permissions.location, 'FINE_LOCATION permission mismatch');
expect(hasPermission('android.permission.RECORD_AUDIO') === permissions.microphone, 'RECORD_AUDIO permission mismatch');

const swipeDep = gradle.includes('androidx.swiperefreshlayout:swiperefreshlayout');
const swipeRef = main.includes('SwipeRefreshLayout');
expect(swipeDep === plan.pullRefresh, `SwipeRefresh dependency mismatch (expected ${plan.pullRefresh})`);
expect(swipeRef === plan.pullRefresh, `SwipeRefresh Java reference mismatch (expected ${plan.pullRefresh})`);

const lottieDep = gradle.includes('com.airbnb.android:lottie');
const lottieRef = main.includes('LottieAnimationView');
expect(lottieDep === plan.lottieLoader, `Lottie dependency mismatch (expected ${plan.lottieLoader})`);
expect(lottieRef === plan.lottieLoader, `Lottie Java reference mismatch (expected ${plan.lottieLoader})`);

if (plan.nativeUi) expect(main.includes('applyNativeChrome(webView);'), 'Native UI requested but applyNativeChrome call missing');
if (plan.header) expect(main.includes('createAppForgeHeader'), 'Header enabled but header runtime missing');
if (plan.bottomNav) expect(main.includes('addAppForgeBottomItem'), 'Bottom Navigation enabled but runtime missing');
if (plan.sidebar) expect(main.includes('installAppForgeSidebar'), 'Sidebar enabled but runtime missing');
if (plan.floatingButton) expect(main.includes('floating.setOnClickListener'), 'Floating Button enabled but runtime missing');
if (plan.floatingButton && String(client.uiNavigation?.floating_button_icon_url || '').trim()) {
  const customFloating = walk(path.join(app, 'src', 'main', 'res', 'drawable')).some((f) => /appforge_floating_icon\.(png|jpg|jpeg|webp)$/i.test(f));
  expect(customFloating, 'Floating Button custom icon configured but native drawable missing');
}
if (plan.pageLoader) expect(main.includes('appForgeLoaderContainer'), 'Page loader requested but native loader missing');
if (plan.pdfViewer) expect(main.includes('appForgePdf(uri)'), 'PDF Viewer enabled but PDF routing missing');

expect(main.includes('installAppForgeWebViewClient(webView);'), 'AppForge WebView client missing');
expect(main.includes('injectAppForgeOverrides'), 'Trusted-origin override injection missing');
expect(main.includes('enforceConfiguredSite(webView);'), 'Configured-site guard missing');
expect(main.includes('OnBackPressedCallback'), 'Android back navigation guard missing');
expect(main.includes(`APPFORGE_EXIT_MODE = ${JSON.stringify(plan.backExitMode)}`), 'Back & Exit mode mismatch');
expect(main.includes(`APPFORGE_DISABLE_BACK = ${plan.disableBack ? 'true' : 'false'}`), 'Disable Back setting mismatch');
if (plan.offlineScreen) expect(main.includes('offline.html'), 'Offline screen runtime missing');
if (plan.errorScreen) expect(main.includes('error.html'), 'Error screen runtime missing');

const biometricDep = gradle.includes('androidx.biometric:biometric');
const biometricRef = main.includes('BiometricPrompt');
expect(biometricDep === plan.biometric, `Biometric dependency mismatch (expected ${plan.biometric})`);
expect(biometricRef === plan.biometric, `Biometric Java reference mismatch (expected ${plan.biometric})`);
if (plan.secureWindow) expect(main.includes('FLAG_SECURE'), 'Screenshot protection requested but FLAG_SECURE missing');
if (plan.keepAwake) expect(main.includes('FLAG_KEEP_SCREEN_ON'), 'Keep-awake requested but flag missing');

const googleServices = fs.existsSync(path.join(app, 'google-services.json'));
const fcmDep = gradle.includes('com.google.firebase:firebase-messaging');
const oneSignalDep = gradle.includes('com.onesignal:OneSignal');
const pushService = manifest.includes('GaotusFirebaseMessagingService');
if (plan.notifications === 'none') {
  expect(!googleServices, 'google-services.json present while notifications disabled');
  expect(!fcmDep, 'Firebase messaging dependency present while notifications disabled');
  expect(!oneSignalDep, 'OneSignal dependency present while notifications disabled');
  expect(!pushService, 'Push service present while notifications disabled');
  expect(!hasPermission('android.permission.POST_NOTIFICATIONS'), 'POST_NOTIFICATIONS permission present while notifications disabled');
} else {
  expect(googleServices, 'Push enabled but google-services.json missing');
  expect(fcmDep, 'Push enabled but Firebase messaging dependency missing');
  expect(pushService, 'Push enabled but messaging service missing');
  expect(hasPermission('android.permission.POST_NOTIFICATIONS'), 'Push enabled but POST_NOTIFICATIONS permission missing');
  if (plan.notifications === 'onesignal') expect(oneSignalDep, 'OneSignal enabled but dependency missing');
}
if (plan.deepLinking) expect(manifest.includes('android:autoVerify="true"') && manifest.includes(`android:host="${plan.host}"`), 'Deep linking enabled but verified intent filter missing');
if (plan.customScheme) expect(manifest.includes(`android:scheme="${plan.customScheme}"`), 'Custom scheme enabled but intent filter missing');

if (errors.length) {
  console.error('[AppForge] Android runtime verification FAILED');
  for (const error of errors) console.error(` - ${error}`);
  process.exit(1);
}
const report = { ok: true, appId: client.appId, appName: client.appName, url: client.url || null, versionName: client.versionName, versionCode: client.versionCode, permissions, plan, verifiedAt: new Date().toISOString() };
fs.writeFileSync(path.join(rootDir, 'runtime-verification.json'), JSON.stringify(report, null, 2) + '\n');
console.log('[AppForge] Android runtime verification PASS', JSON.stringify({ ...plan, permissions }));
