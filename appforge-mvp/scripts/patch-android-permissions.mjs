import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const manifestPath = path.join(rootDir, 'android', 'app', 'src', 'main', 'AndroidManifest.xml');
if (!fs.existsSync(manifestPath)) throw new Error('AndroidManifest.xml missing');

const features = client.features || {};
const configured = client.permissions || {};
const boolOr = (key, fallback) => typeof configured[key] === 'boolean' ? configured[key] : fallback;
const effective = {
  camera: boolOr('camera', features.camera === true),
  location: boolOr('location', features.location === true),
  microphone: boolOr('microphone', false),
  vibration: boolOr('vibration', features.haptics === true),
};

const managed = [
  'android.permission.CAMERA',
  'android.permission.VIBRATE',
  'android.permission.ACCESS_COARSE_LOCATION',
  'android.permission.ACCESS_FINE_LOCATION',
  'android.permission.RECORD_AUDIO',
];

let xml = fs.readFileSync(manifestPath, 'utf8');
for (const permission of managed) {
  const escaped = permission.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  xml = xml.replace(new RegExp(`\\s*<uses-permission\\s+android:name=["']${escaped}["']\\s*/>`, 'g'), '');
}

const wanted = [];
if (effective.camera) wanted.push('android.permission.CAMERA');
if (effective.vibration) wanted.push('android.permission.VIBRATE');
if (effective.location) {
  wanted.push('android.permission.ACCESS_COARSE_LOCATION');
  wanted.push('android.permission.ACCESS_FINE_LOCATION');
}
if (effective.microphone) wanted.push('android.permission.RECORD_AUDIO');

if (wanted.length) {
  const block = wanted.map((permission) => `    <uses-permission android:name="${permission}" />`).join('\n');
  if (!xml.includes('<application')) throw new Error('AndroidManifest application marker missing');
  xml = xml.replace('<application', `${block}\n\n    <application`);
}

fs.writeFileSync(manifestPath, xml);
console.log('[AppForge] Android managed permissions normalized', JSON.stringify(effective));
