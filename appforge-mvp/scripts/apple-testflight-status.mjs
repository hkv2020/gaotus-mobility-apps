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
  try { body = text ? JSON.parse(text) : null; } catch { body = { raw: text.slice(0, 1200) }; }
  if (!response.ok) {
    const details = Array.isArray(body?.errors)
      ? body.errors.map((e) => `${e.status || response.status} ${e.code || ''} ${e.title || ''}: ${e.detail || ''}`.trim()).join('\n')
      : `${response.status} ${response.statusText}`;
    throw new Error(`App Store Connect API GET ${pathname} failed:\n${details}`);
  }
  return body;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const configPath = process.argv[2] || 'clients/runtime-builder.json';
const outputPath = process.argv[3] || 'build/testflight/testflight-status.json';
const config = validateClient(readJSON(configPath));

const issuerId = String(process.env.APP_STORE_CONNECT_ISSUER_ID || '').trim();
const keyId = String(process.env.APP_STORE_CONNECT_KEY_ID || '').trim();
const keyPath = String(process.env.APP_STORE_CONNECT_KEY_PATH || '').trim();
if (!issuerId || !keyId || !keyPath || !fs.existsSync(keyPath)) throw new Error('Missing App Store Connect credentials');
const privateKey = fs.readFileSync(keyPath, 'utf8');
const token = makeToken({ issuerId, keyId, privateKey });

const appQuery = new URLSearchParams({ 'filter[bundleId]': config.appId, limit: '10' });
const appResponse = await api(token, `/v1/apps?${appQuery.toString()}`);
const app = Array.isArray(appResponse?.data) ? appResponse.data[0] : null;
if (!app?.id) throw new Error(`App Store Connect app record not found for ${config.appId}`);

const expectedBuild = String(config.versionCode);
const timeoutSeconds = Math.max(60, Math.min(1800, Number(process.env.TESTFLIGHT_POLL_TIMEOUT_SECONDS || 900)));
const intervalSeconds = Math.max(10, Math.min(60, Number(process.env.TESTFLIGHT_POLL_INTERVAL_SECONDS || 20)));
const deadline = Date.now() + timeoutSeconds * 1000;
let lastSeen = null;

while (Date.now() < deadline) {
  const q = new URLSearchParams({ 'filter[app]': app.id, sort: '-uploadedDate', limit: '50' });
  const builds = await api(token, `/v1/builds?${q.toString()}`);
  const list = Array.isArray(builds?.data) ? builds.data : [];
  const build = list.find((item) => String(item?.attributes?.version || '') === expectedBuild) || null;
  if (build) {
    lastSeen = build;
    const state = String(build.attributes?.processingState || '').toUpperCase();
    console.log(`[AppForge] TestFlight build ${expectedBuild} processing state: ${state || 'UNKNOWN'}`);
    if (state === 'VALID') {
      const result = {
        checkedAt: new Date().toISOString(),
        appRecordId: app.id,
        bundleIdentifier: config.appId,
        marketingVersion: config.versionName,
        buildNumber: expectedBuild,
        buildResourceId: build.id,
        processingState: state,
        uploadedDate: build.attributes?.uploadedDate || null,
        expirationDate: build.attributes?.expirationDate || null,
        expired: Boolean(build.attributes?.expired),
        minOsVersion: build.attributes?.minOsVersion || null,
        usesNonExemptEncryption: build.attributes?.usesNonExemptEncryption ?? null,
        readyForTestFlight: true,
      };
      fs.mkdirSync(new URL('.', `file://${process.cwd()}/${outputPath}`).pathname, { recursive: true });
      fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + '\n');
      console.log(`[AppForge] TestFlight processing complete for ${config.appId} build ${expectedBuild}.`);
      process.exit(0);
    }
    if (['FAILED', 'INVALID'].includes(state)) {
      throw new Error(`Apple finished processing build ${expectedBuild} with state ${state}`);
    }
  } else {
    console.log(`[AppForge] Waiting for uploaded build ${expectedBuild} to appear in App Store Connect…`);
  }
  await sleep(intervalSeconds * 1000);
}

const state = String(lastSeen?.attributes?.processingState || 'NOT_FOUND').toUpperCase();
const timeoutResult = {
  checkedAt: new Date().toISOString(),
  appRecordId: app.id,
  bundleIdentifier: config.appId,
  marketingVersion: config.versionName,
  buildNumber: expectedBuild,
  buildResourceId: lastSeen?.id || null,
  processingState: state,
  readyForTestFlight: false,
  timedOut: true,
};
fs.mkdirSync(new URL('.', `file://${process.cwd()}/${outputPath}`).pathname, { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(timeoutResult, null, 2) + '\n');
throw new Error(`Timed out waiting for TestFlight processing of build ${expectedBuild}; last state ${state}`);
