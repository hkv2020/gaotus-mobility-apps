import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { rootDir, readJSON } from './lib.mjs';

const buildId = String(process.argv[2] || '').trim();
const ipaPath = path.resolve(rootDir, process.argv[3] || 'build/testflight/Gaotus-TestFlight.ipa');
const statusPath = path.resolve(rootDir, process.argv[4] || 'build/testflight/testflight-status.json');
if (!buildId) throw new Error('build id required');
if (!fs.existsSync(ipaPath) || fs.statSync(ipaPath).size < 1000) throw new Error(`Signed IPA missing: ${ipaPath}`);
if (!fs.existsSync(statusPath)) throw new Error(`TestFlight status evidence missing: ${statusPath}`);

const verificationPath = path.join(rootDir, 'ios-runtime-verification.json');
const featurePath = path.join(rootDir, 'generated-feature-plan.json');
const configPath = path.join(rootDir, 'generated-client.json');
for (const f of [verificationPath, featurePath, configPath]) if (!fs.existsSync(f)) throw new Error(`Required verified output missing: ${f}`);
const verification = readJSON(verificationPath);
if (!verification.ok) throw new Error('iOS runtime verification did not pass');
const client = readJSON(configPath);
const featurePlan = readJSON(featurePath);
const testflight = readJSON(statusPath);
if (!testflight.readyForTestFlight || String(testflight.processingState || '').toUpperCase() !== 'VALID') {
  throw new Error('App Store Connect has not confirmed this IPA as VALID for TestFlight');
}

const dist = path.join(rootDir, 'dist-ios');
fs.mkdirSync(dist, { recursive: true });
const outputIpa = path.join(dist, `${buildId}.ipa`);
fs.copyFileSync(ipaPath, outputIpa);
const sha = crypto.createHash('sha256').update(fs.readFileSync(outputIpa)).digest('hex');
const bytes = fs.statSync(outputIpa).size;

const reportPath = path.join(dist, `${buildId}-ios-build-report.json`);
let report = {
  verified: true,
  platform: 'ios',
  buildId,
  factoryVersion: client.factoryVersion || null,
  appId: client.appId,
  appName: client.appName,
  url: client.url || null,
  versionName: client.versionName,
  versionCode: client.versionCode,
  artifacts: {},
  signedIpa: true,
  testflightUploaded: true,
  generatedAt: new Date().toISOString(),
};
if (fs.existsSync(reportPath)) {
  try {
    const existing = readJSON(reportPath);
    report = { ...report, ...existing, artifacts: { ...(existing.artifacts || {}) }, signedIpa: true, testflightUploaded: true };
  } catch {}
}
report.platform = report.artifacts?.ios_simulator ? 'ios-simulator+testflight' : 'ios-testflight';
report.artifacts.ipa = { file: path.basename(outputIpa), sha256: sha, bytes };
report.testflight = testflight;
report.generatedAt = new Date().toISOString();

fs.copyFileSync(verificationPath, path.join(dist, `${buildId}-ios-verification.json`));
fs.writeFileSync(path.join(dist, `${buildId}-ios-feature-plan.json`), JSON.stringify(featurePlan, null, 2) + '\n');
fs.writeFileSync(path.join(dist, `${buildId}-ios-config.json`), JSON.stringify(client, null, 2) + '\n');
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
fs.copyFileSync(statusPath, path.join(dist, `${buildId}-testflight-status.json`));

const sumsPath = path.join(dist, `${buildId}-ios-SHA256SUMS.txt`);
let existingSums = '';
if (fs.existsSync(sumsPath)) existingSums = fs.readFileSync(sumsPath, 'utf8').trim();
const lines = existingSums ? existingSums.split(/\r?\n/).filter(Boolean) : [];
const ipaLine = `${sha}  ${path.basename(outputIpa)}`;
const filtered = lines.filter((line) => !line.endsWith(`  ${path.basename(outputIpa)}`));
filtered.push(ipaLine);
fs.writeFileSync(sumsPath, filtered.join('\n') + '\n');
console.log('[AppForge] signed iOS TestFlight package ready', JSON.stringify({ file: path.basename(outputIpa), bytes, sha256: sha, buildResourceId: testflight.buildResourceId || null }));
