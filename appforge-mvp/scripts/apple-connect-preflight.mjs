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

async function api(token, pathname, options = {}) {
  const response = await fetch(`https://api.appstoreconnect.apple.com${pathname}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = { raw: text.slice(0, 1000) }; }
  if (!response.ok) {
    const details = Array.isArray(body?.errors)
      ? body.errors.map((e) => `${e.status || response.status} ${e.code || ''} ${e.title || ''}: ${e.detail || ''}`.trim()).join('\n')
      : `${response.status} ${response.statusText}`;
    throw new Error(`App Store Connect API ${options.method || 'GET'} ${pathname} failed:\n${details}`);
  }
  return body;
}

const configPath = process.argv[2] || 'clients/runtime-builder.json';
const config = validateClient(readJSON(configPath));
const issuerId = String(process.env.APP_STORE_CONNECT_ISSUER_ID || '').trim();
const keyId = String(process.env.APP_STORE_CONNECT_KEY_ID || '').trim();
const keyPath = String(process.env.APP_STORE_CONNECT_KEY_PATH || '').trim();
const registerBundle = String(process.env.APPLE_REGISTER_BUNDLE_ID || 'true') === 'true';
const requireAppRecord = String(process.env.APPLE_REQUIRE_APP_RECORD || 'true') === 'true';

if (!issuerId || !keyId || !keyPath) throw new Error('Missing App Store Connect issuer, key ID, or key path');
if (!fs.existsSync(keyPath)) throw new Error(`App Store Connect private key file not found: ${keyPath}`);
const privateKey = fs.readFileSync(keyPath, 'utf8');
if (!privateKey.includes('BEGIN PRIVATE KEY')) throw new Error('App Store Connect private key is not a valid .p8 private key');

const token = makeToken({ issuerId, keyId, privateKey });

// Verify credentials first without logging any secret material.
await api(token, '/v1/apps?limit=1');

const bundleQuery = new URLSearchParams({ 'filter[identifier]': config.appId, limit: '10' });
let bundleResponse = await api(token, `/v1/bundleIds?${bundleQuery.toString()}`);
let bundle = Array.isArray(bundleResponse?.data) ? bundleResponse.data[0] : null;
let bundleCreated = false;

if (!bundle && registerBundle) {
  const safeName = `${String(config.appName || 'AppForge App').slice(0, 80)} AppForge`;
  const created = await api(token, '/v1/bundleIds', {
    method: 'POST',
    body: JSON.stringify({
      data: {
        type: 'bundleIds',
        attributes: {
          identifier: config.appId,
          name: safeName,
          platform: 'IOS',
        },
      },
    }),
  });
  bundle = created?.data || null;
  bundleCreated = Boolean(bundle);
}

if (!bundle) throw new Error(`Bundle ID ${config.appId} is not registered and could not be created`);

const appQuery = new URLSearchParams({ 'filter[bundleId]': config.appId, limit: '10' });
const appsResponse = await api(token, `/v1/apps?${appQuery.toString()}`);
const app = Array.isArray(appsResponse?.data) ? appsResponse.data[0] : null;

const report = {
  checkedAt: new Date().toISOString(),
  bundleIdentifier: config.appId,
  appName: config.appName,
  apiAuthentication: 'ok',
  bundleIdRegistered: true,
  bundleIdCreatedNow: bundleCreated,
  bundleIdResourceId: bundle.id,
  appRecordExists: Boolean(app),
  appResourceId: app?.id || null,
};
fs.writeFileSync('apple-connect-preflight.json', JSON.stringify(report, null, 2) + '\n');
console.log(`[AppForge] Apple API auth OK; bundle ID ${config.appId} ${bundleCreated ? 'registered now' : 'already registered'}.`);

if (!app && requireAppRecord) {
  throw new Error([
    `No App Store Connect app record exists for ${config.appId}.`,
    'Apple currently requires new app records to be created in the App Store Connect website.',
    `Create Apps → + → New App, choose iOS, name "${config.appName}", and select Bundle ID ${config.appId}.`,
    'After the app record exists, rerun this workflow; signing and TestFlight upload will continue automatically.',
  ].join('\n'));
}

if (app) console.log(`[AppForge] App Store Connect app record found: ${app.id}`);
