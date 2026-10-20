import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, out); else out.push(full);
  }
  return out;
}

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const fh = client.fileHandling || {};
const dev = client.deviceHardware || {};
const downloads = fh.downloads_enabled === true;
const publicDownloads = fh.download_to_public !== false;
const clipboard = dev.clipboard_enabled === true;
const appSettings = dev.open_app_settings === true;

const java = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
const mainFiles = java.filter((f) => /MainActivity\.java$/.test(f));
const bridgeFiles = java.filter((f) => /GaotusNativeBridge\.java$/.test(f));
if (mainFiles.length !== 1 || bridgeFiles.length !== 1) throw new Error('AppForge device tools verifier could not resolve Android Java sources');
const main = fs.readFileSync(mainFiles[0], 'utf8');
const bridge = fs.readFileSync(bridgeFiles[0], 'utf8');
const manifest = fs.readFileSync(path.join(rootDir, 'android', 'app', 'src', 'main', 'AndroidManifest.xml'), 'utf8');
const errors = [];
const expect = (condition, message) => { if (!condition) errors.push(message); };

expect(main.includes('injectAppForgeNativeSdk(WebView view, String url)'), 'trusted-origin GaotusNative SDK injection missing');
expect(main.includes('injectAppForgeNativeSdk(view, url);'), 'trusted-origin GaotusNative SDK is not activated on page finish');

expect(main.includes('setDownloadListener') === downloads, `DownloadListener mismatch (expected ${downloads})`);
expect(main.includes('DownloadManager.Request') === downloads, `DownloadManager runtime mismatch (expected ${downloads})`);
if (downloads && publicDownloads) {
  expect(manifest.includes('android.permission.WRITE_EXTERNAL_STORAGE') && manifest.includes('android:maxSdkVersion="28"'), 'legacy public Downloads permission guard missing');
}
if (!downloads) expect(!manifest.includes('android.permission.WRITE_EXTERNAL_STORAGE'), 'legacy storage permission present while native downloads disabled');

expect(bridge.includes('public String copyToClipboard(String text)') === clipboard, `Clipboard bridge mismatch (expected ${clipboard})`);
expect(main.includes('copyToClipboard:function') === clipboard, `Clipboard trusted SDK wrapper mismatch (expected ${clipboard})`);
expect(bridge.includes('public String openAppSettings()') === appSettings, `Open App Settings bridge mismatch (expected ${appSettings})`);
expect(main.includes('openAppSettings:function') === appSettings, `Open App Settings trusted SDK wrapper mismatch (expected ${appSettings})`);

if (errors.length) {
  console.error('[AppForge] Android device tools verification FAILED');
  for (const error of errors) console.error(` - ${error}`);
  process.exit(1);
}

fs.writeFileSync(path.join(rootDir, 'device-tools-verification.json'), JSON.stringify({
  ok: true,
  downloads,
  publicDownloads: downloads && publicDownloads,
  wifiOnly: downloads && fh.wifi_only === true,
  clipboard,
  openAppSettings: appSettings,
  trustedWebSdk: true,
  verifiedAt: new Date().toISOString()
}, null, 2) + '\n');
console.log('[AppForge] Android device tools verification PASS');
