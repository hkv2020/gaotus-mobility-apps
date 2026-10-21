import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
if (client.mode !== 'remote') {
  console.log('[AppForge] iOS remote-web privacy verification not required for local mode');
  process.exit(0);
}

const plistPath = path.join(rootDir, 'ios', 'App', 'App', 'Info.plist');
const reportPath = path.join(rootDir, 'ios-web-privacy-hardening.json');
if (!fs.existsSync(plistPath)) throw new Error('Info.plist missing');
if (!fs.existsSync(reportPath)) throw new Error('iOS web privacy hardening report missing');
const plist = fs.readFileSync(plistPath, 'utf8');
const report = readJSON(reportPath);

const keyDepths = (xml, wantedKey) => {
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

const required = ['NSCameraUsageDescription', 'NSMicrophoneUsageDescription', 'NSLocationWhenInUseUsageDescription'];
const errors = [];
for (const key of required) {
  const depths = keyDepths(plist, key);
  if (depths.length !== 1) errors.push(`${key} must exist exactly once in final Info.plist`);
  else if (depths[0] !== 1) errors.push(`${key} must be top-level in final Info.plist`);
  const valueMatch = plist.match(new RegExp(`<key>${key}<\\/key>\\s*<string>([^<]+)<\\/string>`));
  if (!valueMatch || !String(valueMatch[1] || '').trim()) errors.push(`${key} must contain a non-empty purpose string`);
}
if (report.ok !== true || report.bundleIdentifier !== client.appId) errors.push('iOS web privacy hardening report mismatch');
if (errors.length) {
  console.error('[AppForge] final iOS remote-web privacy verification FAILED');
  for (const error of errors) console.error(` - ${error}`);
  process.exit(1);
}
console.log('[AppForge] final iOS remote-web privacy verification PASS', JSON.stringify({ appId: client.appId, keys: required }));
