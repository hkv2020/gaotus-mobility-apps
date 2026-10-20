import fs from 'node:fs';
import path from 'node:path';
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
const ensureStringKey = (xml, key, value) => {
  if (xml.includes(`<key>${key}</key>`)) return xml;
  return xml.replace('</dict>', `\n\t<key>${key}</key>\n\t<string>${String(value).replace(/[&<>]/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))}</string>\n</dict>`);
};
if (permissions.camera === true) plist = ensureStringKey(plist, 'NSCameraUsageDescription', `${client.appName} uses the camera when you request it.`);
else plist = removePlistKey(plist, 'NSCameraUsageDescription');
if (permissions.location === true) plist = ensureStringKey(plist, 'NSLocationWhenInUseUsageDescription', `${client.appName} uses your location when you request it.`);
else plist = removePlistKey(plist, 'NSLocationWhenInUseUsageDescription');
if (permissions.microphone === true) plist = ensureStringKey(plist, 'NSMicrophoneUsageDescription', `${client.appName} uses the microphone when you request it.`);
else plist = removePlistKey(plist, 'NSMicrophoneUsageDescription');
fs.writeFileSync(plistPath, plist);

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
console.log('[AppForge] iOS runtime patched', JSON.stringify({appId:client.appId, versionName:client.versionName, versionCode:client.versionCode, rtl, camera:permissions.camera===true, location:permissions.location===true, microphone:permissions.microphone===true}));
