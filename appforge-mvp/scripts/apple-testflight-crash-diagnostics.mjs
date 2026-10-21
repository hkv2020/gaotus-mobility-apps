import fs from 'node:fs';
import crypto from 'node:crypto';
import { readJSON, validateClient } from './lib.mjs';

const base64url = (value) => Buffer.from(value).toString('base64url');
const json64 = (value) => base64url(JSON.stringify(value));

function makeToken({ issuerId, keyId, privateKey }) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: 'ES256', kid: keyId, typ: 'JWT' };
  const payload = { iss: issuerId, iat: now, exp: now + 600, aud: 'appstoreconnect-v1' };
  const signingInput = `${json64(header)}.${json64(payload)}`;
  const signature = crypto.sign('sha256', Buffer.from(signingInput), {
    key: privateKey,
    dsaEncoding: 'ieee-p1363',
  });
  return `${signingInput}.${signature.toString('base64url')}`;
}

async function api(token, pathname) {
  const response = await fetch(`https://api.appstoreconnect.apple.com${pathname}`, {
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
  });
  const text = await response.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = { raw: text.slice(0, 1000) }; }
  if (!response.ok) {
    const details = Array.isArray(body?.errors)
      ? body.errors.map((e) => `${e.status || response.status} ${e.code || ''} ${e.title || ''}: ${e.detail || ''}`.trim()).join('\n')
      : `${response.status} ${response.statusText}`;
    throw new Error(`App Store Connect API GET ${pathname} failed:\n${details}`);
  }
  return body;
}

function sanitizeCrashLog(raw) {
  const text = String(raw || '');
  if (!text) return '';
  const lines = text.split(/\r?\n/);
  const keepPrefixes = [
    'Process:', 'Identifier:', 'Version:', 'Code Type:', 'Role:',
    'OS Version:', 'Exception Type:', 'Exception Subtype:', 'Exception Codes:',
    'Termination Reason:', 'Triggered by Thread:', 'Last Exception Backtrace:',
    'Application Specific Information:', 'Thread 0 Crashed:', 'Thread 1 Crashed:',
    'Thread 2 Crashed:', 'Thread 3 Crashed:'
  ];
  const out = [];
  let captureFrames = 0;
  for (const line of lines) {
    if (keepPrefixes.some((p) => line.startsWith(p))) {
      out.push(line);
      if (/^(Last Exception Backtrace:|Thread \d+ Crashed:)/.test(line)) captureFrames = 35;
      continue;
    }
    if (captureFrames > 0) {
      if (!line.trim()) {
        if (out.length && out[out.length - 1] !== '') out.push('');
        captureFrames -= 1;
        continue;
      }
      if (/^\d+\s+/.test(line) || /^\s*\d+\s+/.test(line)) {
        out.push(line.replace(/\/Users\/[^/\s]+\//g, '/Users/<redacted>/'));
        captureFrames -= 1;
        continue;
      }
      if (/^Thread \d+/.test(line) && !/Crashed:/.test(line)) {
        captureFrames = 0;
      }
    }
  }
  return out.slice(0, 140).join('\n').trim();
}

const configPath = process.argv[2] || 'clients/gaotus-testflight-smoke.json';
const config = validateClient(readJSON(configPath));
const issuerId = String(process.env.APP_STORE_CONNECT_ISSUER_ID || '').trim();
const keyId = String(process.env.APP_STORE_CONNECT_KEY_ID || '').trim();
const keyPath = String(process.env.APP_STORE_CONNECT_KEY_PATH || '').trim();
if (!issuerId || !keyId || !keyPath) throw new Error('Missing App Store Connect issuer, key ID, or key path');
if (!fs.existsSync(keyPath)) throw new Error(`App Store Connect private key file not found: ${keyPath}`);
const privateKey = fs.readFileSync(keyPath, 'utf8');
if (!privateKey.includes('BEGIN PRIVATE KEY')) throw new Error('App Store Connect private key is not a valid .p8 private key');
const token = makeToken({ issuerId, keyId, privateKey });

const appQuery = new URLSearchParams({ 'filter[bundleId]': config.appId, limit: '10' });
const apps = await api(token, `/v1/apps?${appQuery.toString()}`);
const app = Array.isArray(apps?.data) ? apps.data[0] : null;
if (!app?.id) throw new Error(`App Store Connect app record not found for ${config.appId}`);

const crashQuery = new URLSearchParams({
  limit: '50',
  sort: '-createdDate',
  'fields[betaFeedbackCrashSubmissions]': 'createdDate,deviceModel,osVersion,architecture,appUptimeInMilliseconds,buildBundleId,crashLog,build'
});
const crashes = await api(token, `/v1/apps/${app.id}/betaFeedbackCrashSubmissions?${crashQuery.toString()}`);
const rows = Array.isArray(crashes?.data) ? crashes.data : [];
const report = {
  checkedAt: new Date().toISOString(),
  bundleIdentifier: config.appId,
  appResourceId: app.id,
  crashSubmissionCount: rows.length,
  latest: null,
};

if (!rows.length) {
  fs.writeFileSync('testflight-crash-diagnostics.json', JSON.stringify(report, null, 2) + '\n');
  console.log('[AppForge] No TestFlight crash submissions are available yet.');
  process.exit(0);
}

const latest = rows[0];
const attrs = latest.attributes || {};
let crashText = '';
try {
  const crash = await api(token, `/v1/betaFeedbackCrashSubmissions/${latest.id}/crashLog?fields%5BbetaCrashLogs%5D=logText`);
  crashText = String(crash?.data?.attributes?.logText || '');
} catch (error) {
  console.log(`[AppForge] Crash submission found but crashLog fetch failed: ${error.message}`);
}
const sanitized = sanitizeCrashLog(crashText);
report.latest = {
  id: latest.id,
  createdDate: attrs.createdDate || null,
  deviceModel: attrs.deviceModel || null,
  osVersion: attrs.osVersion || null,
  architecture: attrs.architecture || null,
  appUptimeInMilliseconds: attrs.appUptimeInMilliseconds ?? null,
  buildBundleId: attrs.buildBundleId || null,
  sanitizedCrashSummary: sanitized || null,
};
fs.writeFileSync('testflight-crash-diagnostics.json', JSON.stringify(report, null, 2) + '\n');
console.log(`[AppForge] TestFlight crash submissions: ${rows.length}`);
console.log(`[AppForge] Latest crash: ${attrs.createdDate || 'unknown date'} | ${attrs.deviceModel || 'unknown device'} | iOS ${attrs.osVersion || 'unknown'} | uptime ${attrs.appUptimeInMilliseconds ?? 'unknown'} ms`);
if (sanitized) {
  console.log('--- APPFORGE SANITIZED CRASH SUMMARY ---');
  console.log(sanitized);
  console.log('--- END APPFORGE SANITIZED CRASH SUMMARY ---');
} else {
  console.log('[AppForge] Latest crash submission currently has no readable crash log text.');
}
