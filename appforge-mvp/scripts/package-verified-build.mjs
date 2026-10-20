import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { rootDir, readJSON } from './lib.mjs';

const rawId = String(process.argv[2] || process.env.BUILD_ID || '').trim();
if (!/^[A-Za-z0-9._-]{1,120}$/.test(rawId)) throw new Error('Valid build ID required');
const buildId = rawId;
const dist = path.join(rootDir, 'dist');
fs.mkdirSync(dist, { recursive: true });

const source = {
  apk: path.join(rootDir, 'android', 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk'),
  aab: path.join(rootDir, 'android', 'app', 'build', 'outputs', 'bundle', 'release', 'app-release.aab'),
};
for (const [kind, file] of Object.entries(source)) {
  if (!fs.existsSync(file) || fs.statSync(file).size < 1) throw new Error(`${kind.toUpperCase()} output missing`);
}

const verificationPath = path.join(rootDir, 'runtime-verification.json');
const featurePlanPath = path.join(rootDir, 'generated-feature-plan.json');
const configPath = path.join(rootDir, 'generated-client.json');
for (const file of [verificationPath, featurePlanPath, configPath]) if (!fs.existsSync(file)) throw new Error(`Required factory report missing: ${path.basename(file)}`);
const verification = readJSON(verificationPath);
if (verification.ok !== true) throw new Error('Runtime verification report is not successful');

const targets = {
  apk: path.join(dist, `${buildId}.apk`),
  aab: path.join(dist, `${buildId}.aab`),
};
fs.copyFileSync(source.apk, targets.apk);
fs.copyFileSync(source.aab, targets.aab);
fs.copyFileSync(verificationPath, path.join(dist, `${buildId}-verification.json`));
fs.copyFileSync(featurePlanPath, path.join(dist, `${buildId}-feature-plan.json`));

const config = readJSON(configPath);
delete config.firebaseGoogleServicesB64;
fs.writeFileSync(path.join(dist, `${buildId}-config.json`), JSON.stringify(config, null, 2) + '\n');

const artifacts = {};
for (const [kind, file] of Object.entries(targets)) {
  const body = fs.readFileSync(file);
  artifacts[kind] = {
    filename: path.basename(file),
    bytes: body.length,
    sha256: crypto.createHash('sha256').update(body).digest('hex'),
  };
}

const report = {
  schemaVersion: 1,
  factoryVersion: String(config.factoryVersion || '0.4.0'),
  buildId,
  verified: true,
  appId: config.appId,
  url: config.url || null,
  verification,
  artifacts,
};
fs.writeFileSync(path.join(dist, `${buildId}-build-report.json`), JSON.stringify(report, null, 2) + '\n');
fs.writeFileSync(path.join(dist, `${buildId}-SHA256SUMS.txt`), `${artifacts.apk.sha256}  ${artifacts.apk.filename}\n${artifacts.aab.sha256}  ${artifacts.aab.filename}\n`);
console.log('[AppForge] verified build package prepared', JSON.stringify({ buildId, artifacts }));
