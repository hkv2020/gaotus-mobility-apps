import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const plistPath = path.join(rootDir, 'ios', 'App', 'App', 'Info.plist');
if (!fs.existsSync(plistPath)) throw new Error(`Info.plist missing: ${plistPath}`);

// Remote web content can call browser capture/geolocation APIs independently of the
// AppForge native-feature toggles. iOS raises an exception if protected APIs are
// reached without the matching purpose string. Until AppForge enforces those web
// APIs at WKWebView delegate level, remote wrappers must ship defensive purpose
// strings. Presence of a purpose string does NOT request permission by itself.
if (client.mode !== 'remote') {
  console.log('[AppForge] iOS remote-web privacy hardening not required for local mode');
  process.exit(0);
}

let plist = fs.readFileSync(plistPath, 'utf8');
const escapeXml = (value) => String(value).replace(/[&<>]/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]));
const removeStringKey = (xml, key) => xml.replace(new RegExp(`\\s*<key>${key}<\\/key>\\s*<string>[\\s\\S]*?<\\/string>`, 'g'), '');
const rootDictClose = (xml) => {
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
    }
  }
  throw new Error('Info.plist root </dict> missing');
};
const putTopLevelString = (xml, key, value) => {
  const clean = removeStringKey(xml, key);
  const close = rootDictClose(clean);
  const block = `\n\t<key>${key}</key>\n\t<string>${escapeXml(value)}</string>`;
  return clean.slice(0, close) + block + '\n' + clean.slice(close);
};

const app = client.appName || 'This app';
const required = {
  NSCameraUsageDescription: `${app} uses the camera only when a website feature you choose requests camera access.`,
  NSMicrophoneUsageDescription: `${app} uses the microphone only when a website feature you choose requests microphone access.`,
  NSLocationWhenInUseUsageDescription: `${app} uses your location only while the app is open and a website feature you choose requests it.`
};
for (const [key, value] of Object.entries(required)) plist = putTopLevelString(plist, key, value);
fs.writeFileSync(plistPath, plist);

const report = {
  ok: true,
  mode: client.mode,
  bundleIdentifier: client.appId,
  purposeStrings: Object.keys(required),
  permissionRequestOnLaunch: false,
  reason: 'Remote WKWebView content may reach protected web APIs independently of native feature toggles.',
  hardenedAt: new Date().toISOString()
};
fs.writeFileSync(path.join(rootDir, 'ios-web-privacy-hardening.json'), JSON.stringify(report, null, 2) + '\n');
console.log('[AppForge] iOS remote-web privacy hardening applied', JSON.stringify(report.purposeStrings));
