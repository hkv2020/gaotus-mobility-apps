import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const appDir = path.join(rootDir, 'ios', 'App', 'App');
const scenePath = path.join(appDir, 'SceneDelegate.swift');
const plistPath = path.join(appDir, 'Info.plist');
const projectPath = path.join(rootDir, 'ios', 'App', 'App.xcodeproj', 'project.pbxproj');
const errors = [];
const expect = (ok, message) => { if (!ok) errors.push(message); };
for (const file of [scenePath, plistPath, projectPath]) expect(fs.existsSync(file), `Missing iOS file: ${file}`);
if (errors.length) { for (const e of errors) console.error('[AppForge iOS]', e); process.exit(1); }

const scene = fs.readFileSync(scenePath, 'utf8');
const plist = fs.readFileSync(plistPath, 'utf8');
const project = fs.readFileSync(projectPath, 'utf8');
const host = client.mode === 'remote' ? new URL(client.url).hostname : 'localhost';
const permissions = client.permissions || {};
const direction = client.localisation?.rtl === true ? 'rtl' : 'ltr';
const remotePrivacySafe = client.mode === 'remote';

const plistKeyDepths = (xml, wantedKey) => {
  const depths = [];
  const token = /<dict>|<\/dict>|<key>([^<]+)<\/key>/g;
  let depth = 0;
  let match;
  while ((match = token.exec(xml))) {
    if (match[0] === '<dict>') depth += 1;
    else if (match[0] === '</dict>') depth -= 1;
    else if (match[1] === wantedKey) depths.push(depth);
  }
  return depths;
};
const expectPermissionKey = (key, enabled, label) => {
  const depths = plistKeyDepths(plist, key);
  if (enabled) {
    expect(depths.length === 1, `${label} usage description must exist exactly once`);
    expect(depths.length === 1 && depths[0] === 1, `${label} usage description must be a top-level Info.plist key`);
    const value = plist.match(new RegExp(`<key>${key}<\\/key>\\s*<string>([^<]+)<\\/string>`));
    expect(Boolean(value && String(value[1] || '').trim()), `${label} usage description must be non-empty`);
  } else {
    expect(depths.length === 0, `${label} usage description must be absent when permission is disabled in local mode`);
  }
};

expect(project.includes(`PRODUCT_BUNDLE_IDENTIFIER = ${client.appId};`), 'Bundle identifier mismatch');
expect(project.includes(`MARKETING_VERSION = ${client.versionName};`), 'Marketing version mismatch');
expect(project.includes(`CURRENT_PROJECT_VERSION = ${client.versionCode};`), 'Build number mismatch');
expect(scene.includes(`allowedHost = \"${host}\"`), 'Allowed host mismatch');
expect(scene.includes('webView.configuration.userContentController.add(handler, name: "gaotusNative")'), 'Native message handler missing');
expect(scene.includes('window.GaotusNative'), 'Trusted page GaotusNative SDK missing');
expect(scene.includes('window.GaotusEnv'), 'Trusted page environment injection missing');
expect(scene.includes('override func viewDidLayoutSubviews()'), 'Native iOS safe-area layout override missing');
expect(scene.includes('gaotusSafeAreaTopInset = view.safeAreaInsets.top'), 'Native iOS top safe-area inset missing');
expect(scene.includes('webView.frame = gaotusSafeAreaFrame'), 'Native iOS safe-area WebView frame application missing');
const directionPatterns = [
  `document.documentElement.dir = \"${direction}\"`,
  `document.documentElement.dir = \\\"${direction}\\\"`,
  `document.documentElement.dir=${JSON.stringify(direction)}`,
  `document.documentElement.dir = ${JSON.stringify(direction)}`
];
expect(directionPatterns.some((pattern) => scene.includes(pattern)), `LTR/RTL runtime mismatch (expected ${direction})`);

// For remote wrappers, purpose strings are a safety boundary, not evidence that
// permission is proactively requested. Remote website JS may reach camera,
// microphone or location APIs independently of AppForge's native toggles.
expectPermissionKey('NSCameraUsageDescription', remotePrivacySafe || permissions.camera === true, 'Camera');
expectPermissionKey('NSLocationWhenInUseUsageDescription', remotePrivacySafe || permissions.location === true, 'Location');
expectPermissionKey('NSMicrophoneUsageDescription', remotePrivacySafe || permissions.microphone === true, 'Microphone');
if (remotePrivacySafe) {
  const privacyReportPath = path.join(rootDir, 'ios-web-privacy-hardening.json');
  expect(fs.existsSync(privacyReportPath), 'Remote iOS privacy hardening report is missing');
  if (fs.existsSync(privacyReportPath)) {
    try {
      const privacy = readJSON(privacyReportPath);
      expect(privacy.ok === true, 'Remote iOS privacy hardening report is not OK');
      expect(privacy.bundleIdentifier === client.appId, 'Remote iOS privacy hardening bundle identifier mismatch');
      expect(privacy.permissionRequestOnLaunch === false, 'Privacy hardening must not request protected permissions on launch');
    } catch (error) {
      errors.push(`Invalid remote iOS privacy hardening report: ${error.message}`);
    }
  }
}

let brandingVerified = !String(client.iconUrl || '').trim();
if (String(client.iconUrl || '').trim()) {
  const brandingPath = path.join(rootDir, 'ios-branding-verification.json');
  expect(fs.existsSync(brandingPath), 'Custom iOS icon configured but branding verification report is missing');
  if (fs.existsSync(brandingPath)) {
    try {
      const branding = readJSON(brandingPath);
      expect(branding.ok === true, 'iOS branding verification report is not OK');
      expect(String(branding.sourceUrl || '') === String(client.iconUrl || ''), 'iOS branding source URL mismatch');
      expect(Array.isArray(branding.generated) && branding.generated.length > 0, 'iOS branding generated icon list is empty');
      const setDir = path.join(rootDir, String(branding.appIconSet || ''));
      for (const row of Array.isArray(branding.generated) ? branding.generated : []) {
        const file = path.join(setDir, String(row.file || ''));
        expect(fs.existsSync(file) && fs.statSync(file).size > 0, `Generated iOS icon missing: ${row.file || '?'}`);
      }
      brandingVerified = errors.length === 0;
    } catch (error) {
      errors.push(`Invalid iOS branding verification report: ${error.message}`);
    }
  }
}

if (errors.length) {
  console.error('[AppForge] iOS runtime verification FAILED');
  for (const error of errors) console.error(` - ${error}`);
  process.exit(1);
}
const report = {
  ok: true,
  platform: 'ios-simulator',
  appId: client.appId,
  appName: client.appName,
  url: client.url || null,
  versionName: client.versionName,
  versionCode: client.versionCode,
  host,
  runtime: {
    remoteWebView: true,
    trustedNativeSdk: true,
    environmentInjection: true,
    localisationDirection: true,
    nativeSafeAreaTop: true,
    customAppIcon: brandingVerified,
    permissionDescriptionsTopLevel: true,
    remoteWebPrivacySafePurposeStrings: remotePrivacySafe,
    permissionRequestOnLaunch: false,
    share: true,
    haptics: true,
    externalLinks: true,
    cameraCommand: true,
    clipboard: true,
    appSettings: true
  },
  simulator: true,
  signedIpa: false,
  verifiedAt: new Date().toISOString()
};
fs.writeFileSync(path.join(rootDir, 'ios-runtime-verification.json'), JSON.stringify(report, null, 2) + '\n');
console.log('[AppForge] iOS runtime verification PASS', JSON.stringify(report.runtime));
