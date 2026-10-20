import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { rootDir, readJSON } from './lib.mjs';

const buildId = String(process.argv[2] || '').trim();
const appPath = path.resolve(rootDir, process.argv[3] || 'build/ios-sim/Build/Products/Debug-iphonesimulator/App.app');
if (!buildId) throw new Error('build id required');
if (!fs.existsSync(appPath) || !fs.statSync(appPath).isDirectory()) throw new Error(`iOS simulator app bundle missing: ${appPath}`);
const verificationPath = path.join(rootDir, 'ios-runtime-verification.json');
const featurePath = path.join(rootDir, 'generated-feature-plan.json');
const configPath = path.join(rootDir, 'generated-client.json');
for (const f of [verificationPath, featurePath, configPath]) if (!fs.existsSync(f)) throw new Error(`Required verified output missing: ${f}`);
const verification = readJSON(verificationPath);
if (!verification.ok) throw new Error('iOS runtime verification did not pass');
const client = readJSON(configPath);
const featurePlan = readJSON(featurePath);
const dist = path.join(rootDir, 'dist-ios');
fs.rmSync(dist, {recursive:true, force:true});
fs.mkdirSync(dist, {recursive:true});
const zipPath = path.join(dist, `${buildId}-ios-simulator.zip`);
const result = spawnSync('ditto', ['-c','-k','--sequesterRsrc','--keepParent', appPath, zipPath], {stdio:'inherit'});
if (result.status !== 0 || !fs.existsSync(zipPath) || fs.statSync(zipPath).size < 1000) throw new Error('Failed to package iOS simulator .app');
const sha = crypto.createHash('sha256').update(fs.readFileSync(zipPath)).digest('hex');
const bytes = fs.statSync(zipPath).size;
const report = {
  verified: true,
  platform: 'ios-simulator',
  buildId,
  factoryVersion: client.factoryVersion || null,
  appId: client.appId,
  appName: client.appName,
  url: client.url || null,
  versionName: client.versionName,
  versionCode: client.versionCode,
  artifacts: { ios_simulator: { file: path.basename(zipPath), sha256: sha, bytes } },
  signedIpa: false,
  generatedAt: new Date().toISOString()
};
fs.copyFileSync(verificationPath, path.join(dist, `${buildId}-ios-verification.json`));
fs.writeFileSync(path.join(dist, `${buildId}-ios-feature-plan.json`), JSON.stringify(featurePlan, null, 2) + '\n');
fs.writeFileSync(path.join(dist, `${buildId}-ios-config.json`), JSON.stringify(client, null, 2) + '\n');
fs.writeFileSync(path.join(dist, `${buildId}-ios-build-report.json`), JSON.stringify(report, null, 2) + '\n');
fs.writeFileSync(path.join(dist, `${buildId}-ios-SHA256SUMS.txt`), `${sha}  ${path.basename(zipPath)}\n`);
console.log('[AppForge] iOS simulator package ready', JSON.stringify({file:path.basename(zipPath), bytes, sha256:sha}));
