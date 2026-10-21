import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { rootDir, readJSON, validateClient } from './lib.mjs';

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
if (!['ios', 'both'].includes(String(client.platform || 'ios'))) {
  console.log('[AppForge] iOS runtime requested for a non-iOS config; continuing for smoke compatibility');
}

const appDir = path.join(rootDir, 'ios', 'App', 'App');
const scenePath = path.join(appDir, 'SceneDelegate.swift');
const plistPath = path.join(appDir, 'Info.plist');
const projectPath = path.join(rootDir, 'ios', 'App', 'App.xcodeproj', 'project.pbxproj');
for (const file of [scenePath, plistPath, projectPath]) if (!fs.existsSync(file)) throw new Error(`Required iOS file missing: ${file}`);

if (!/^[A-Za-z][A-Za-z0-9]*(\.[A-Za-z][A-Za-z0-9]*){2,}$/.test(String(client.appId || ''))) {
  throw new Error('iOS bundle identifier must use letters/numbers and dots only, with at least 3 segments');
}

let project = fs.readFileSync(projectPath, 'utf8');
project = project.replace(/PRODUCT_BUNDLE_IDENTIFIER\s*=\s*[^;]+;/g, `PRODUCT_BUNDLE_IDENTIFIER = ${client.appId};`);
project = project.replace(/MARKETING_VERSION\s*=\s*[^;]+;/g, `MARKETING_VERSION = ${client.versionName};`);
project = project.replace(/CURRENT_PROJECT_VERSION\s*=\s*[^;]+;/g, `CURRENT_PROJECT_VERSION = ${client.versionCode};`);
fs.writeFileSync(projectPath, project);

const permissions = client.permissions || {};
let plist = fs.readFileSync(plistPath, 'utf8');
const removePlistKey = (xml, key) => xml.replace(new RegExp(`\\s*<key>${key}<\\/key>\\s*<string>[\\s\\S]*?<\\/string>`, 'g'), '');
const escapeXml = (value) => String(value).replace(/[&<>]/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));
const topLevelDictClose = (xml) => {
  const start = xml.indexOf('<dict>');
  if (start < 0) throw new Error('Info.plist root <dict> missing');
  const token = /<dict>|<\/dict>/g;
  token.lastIndex = start;
  let depth = 0;
  let match;
  while ((match = token.exec(xml))) {
    if (match[0] === '<dict>') depth += 1;
    else {
      depth -= 1;
      if (depth === 0) return match.index;
      if (depth < 0) break;
    }
  }
  throw new Error('Info.plist root </dict> missing');
};
const ensureTopLevelStringKey = (xml, key, value) => {
  const clean = removePlistKey(xml, key);
  const close = topLevelDictClose(clean);
  const block = `\n\t<key>${key}</key>\n\t<string>${escapeXml(value)}</string>`;
  return clean.slice(0, close) + block + '\n' + clean.slice(close);
};
if (permissions.camera === true) plist = ensureTopLevelStringKey(plist, 'NSCameraUsageDescription', `${client.appName} uses the camera when you request it.`);
else plist = removePlistKey(plist, 'NSCameraUsageDescription');
if (permissions.location === true) plist = ensureTopLevelStringKey(plist, 'NSLocationWhenInUseUsageDescription', `${client.appName} uses your location when you request it.`);
else plist = removePlistKey(plist, 'NSLocationWhenInUseUsageDescription');
if (permissions.microphone === true) plist = ensureTopLevelStringKey(plist, 'NSMicrophoneUsageDescription', `${client.appName} uses the microphone when you request it.`);
else plist = removePlistKey(plist, 'NSMicrophoneUsageDescription');
fs.writeFileSync(plistPath, plist);

async function applyIOSBranding() {
  const iconUrl = String(client.iconUrl || '').trim();
  if (!iconUrl) return null;

  const sourcePath = path.join(rootDir, 'assets', 'icon-only.png');
  const setDir = path.join(appDir, 'Assets.xcassets', 'AppIcon.appiconset');
  const contentsPath = path.join(setDir, 'Contents.json');
  if (!fs.existsSync(sourcePath)) throw new Error('Custom iOS icon was configured but assets/icon-only.png is missing');
  if (!fs.existsSync(contentsPath)) throw new Error('iOS AppIcon.appiconset/Contents.json is missing');

  const sharpModule = await import('sharp');
  const sharp = sharpModule.default;
  const contents = JSON.parse(fs.readFileSync(contentsPath, 'utf8'));
  const images = Array.isArray(contents.images) ? contents.images.filter((row) => row && row.filename) : [];
  if (!images.length) throw new Error('iOS AppIcon Contents.json contains no file-backed icon entries');

  const theme = /^#[0-9a-fA-F]{6}$/.test(String(client.themeColor || '')) ? String(client.themeColor) : '#111827';
  const generated = [];
  for (const row of images) {
    const target = path.join(setDir, String(row.filename));
    let pixels = 0;
    if (fs.existsSync(target)) {
      const existing = await sharp(target).metadata();
      if (Number.isFinite(existing.width) && existing.width > 0 && existing.width === existing.height) pixels = existing.width;
    }
    if (!pixels) {
      const points = Number.parseFloat(String(row.size || '').split('x')[0]);
      const parsedScale = Number.parseFloat(String(row.scale || '1').replace(/x$/i, ''));
      const scale = Number.isFinite(parsedScale) && parsedScale > 0 ? parsedScale : 1;
      if (Number.isFinite(points) && points > 0) pixels = Math.round(points * scale);
    }
    if (!pixels) throw new Error(`Unable to determine iOS AppIcon pixel size for ${row.filename}`);
    await sharp(sourcePath)
      .resize(pixels, pixels, { fit: 'contain', background: theme })
      .flatten({ background: theme })
      .png()
      .toFile(target);
    const meta = await sharp(target).metadata();
    if (meta.width !== pixels || meta.height !== pixels || meta.hasAlpha === true) {
      throw new Error(`Generated iOS AppIcon failed validation: ${row.filename}`);
    }
    generated.push({ file: row.filename, pixels, sha256: crypto.createHash('sha256').update(fs.readFileSync(target)).digest('hex') });
  }

  const report = {
    ok: true,
    sourceUrl: iconUrl,
    sourceSha256: crypto.createHash('sha256').update(fs.readFileSync(sourcePath)).digest('hex'),
    appIconSet: path.relative(rootDir, setDir),
    generated,
    verifiedAt: new Date().toISOString()
  };
  fs.writeFileSync(path.join(rootDir, 'ios-branding-verification.json'), JSON.stringify(report, null, 2) + '\n');
  console.log('[AppForge] iOS AppIcon branding applied', JSON.stringify({ count: generated.length, sourceSha256: report.sourceSha256 }));
  return report;
}

await applyIOSBranding();

let scene = fs.readFileSync(scenePath, 'utf8');
const env = {};
for (const row of Array.isArray(client.environment) ? client.environment : []) {
  const key = String(row?.key || '').trim();
  if (/^[A-Z][A-Z0-9_]*$/.test(key)) env[key] = String(row?.value ?? '');
}
const localisation = client.localisation || {};
const lang = String(localisation.language || 'en').replace(/[^A-Za-z_-]/g, '') || 'en';
const rtl = localisation.rtl === true;
const overrides = client.overrides || {};
const sdk = `(() => {
  try {
    const post = (action, payload = {}) => { try { window.webkit.messageHandlers.gaotusNative.postMessage({action, payload}); return {ok:true, platform:'ios', action, queued:true}; } catch (e) { return {ok:false, platform:'ios', action, error:String(e)}; } };
    window.GaotusNative = Object.freeze({
      ping: () => post('ping'),
      deviceInfo: () => post('deviceInfo'),
      share: (v) => post('share', v || {}),
      haptic: (v) => post('haptic', {type:v || 'medium'}),
      openExternal: (v) => post('openExternal', {url:String(v || '')}),
      openCamera: () => post('openCamera'),
      toast: (v) => post('toast', {message:String(v || '')}),
      copyToClipboard: (v) => post('copyToClipboard', {text:String(v || '')}),
      openAppSettings: () => post('openAppSettings')
    });
    window.GaotusEnv = Object.freeze(${JSON.stringify(env)});
    document.documentElement.lang = ${JSON.stringify(lang)};
    document.documentElement.dir = ${JSON.stringify(rtl ? 'rtl' : 'ltr')};
    const css = ${JSON.stringify(String(overrides.custom_css || ''))};
    if (css) { let s=document.getElementById('gaotus-appforge-css'); if(!s){s=document.createElement('style');s.id='gaotus-appforge-css';document.head.appendChild(s);} s.textContent=css; }
    const js = ${JSON.stringify(String(overrides.custom_js || ''))};
    if (js) { try { (0,eval)(js); } catch(e) { console.warn('AppForge override', e); } }
  } catch (e) { console.warn('AppForge iOS SDK', e); }
})();`;
const sdkSwift = JSON.stringify(sdk);
const handlerMarker = 'webView.configuration.userContentController.add(handler, name: "gaotusNative")';
if (!scene.includes(handlerMarker)) throw new Error('iOS Gaotus bridge handler marker missing');
if (!scene.includes('gaotusAppForgeSdkSource')) {
  scene = scene.replace(handlerMarker, `${handlerMarker}\n        let gaotusAppForgeSdkSource = ${sdkSwift}\n        webView.configuration.userContentController.addUserScript(WKUserScript(source: gaotusAppForgeSdkSource, injectionTime: .atDocumentEnd, forMainFrameOnly: true))`);
}

const safeAreaMethod = `    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        guard let webView = bridge?.webView else { return }
        let gaotusSafeAreaTopInset = view.safeAreaInsets.top
        let gaotusSafeAreaFrame = CGRect(
            x: 0,
            y: gaotusSafeAreaTopInset,
            width: view.bounds.width,
            height: max(0, view.bounds.height - gaotusSafeAreaTopInset)
        )
        if webView.frame != gaotusSafeAreaFrame { webView.frame = gaotusSafeAreaFrame }
        webView.scrollView.contentInsetAdjustmentBehavior = .never
    }
`;
if (!scene.includes('gaotusSafeAreaTopInset')) {
  const deinitMarker = '    deinit {';
  if (!scene.includes(deinitMarker)) throw new Error('iOS GaotusViewController deinit marker missing for safe-area patch');
  scene = scene.replace(deinitMarker, `${safeAreaMethod}\n${deinitMarker}`);
}

const extraCases = `
        case "ping", "deviceInfo":
            break
        case "toast":
            let message = payload["message"] as? String ?? ""
            let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
            vc.present(alert, animated: true)
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { alert.dismiss(animated: true) }
        case "copyToClipboard":
            UIPasteboard.general.string = payload["text"] as? String ?? ""
        case "openAppSettings":
            if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) }
`;
if (!scene.includes('case "copyToClipboard":')) {
  const switchMarker = '        switch action {\n        case "share":';
  if (!scene.includes(switchMarker)) throw new Error('iOS bridge switch marker missing');
  scene = scene.replace(switchMarker, `        switch action {${extraCases}        case "share":`);
}
fs.writeFileSync(scenePath, scene);
console.log('[AppForge] iOS runtime patched', JSON.stringify({appId:client.appId, versionName:client.versionName, versionCode:client.versionCode, rtl, safeAreaTop:true, brandedIcon:Boolean(client.iconUrl), camera:permissions.camera===true, location:permissions.location===true, microphone:permissions.microphone===true}));
