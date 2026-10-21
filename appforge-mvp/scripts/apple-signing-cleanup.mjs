import fs from 'node:fs';
import crypto from 'node:crypto';

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

async function request(token, pathname, options = {}) {
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
  if (!response.ok && response.status !== 404) {
    let body = null;
    try { body = text ? JSON.parse(text) : null; } catch {}
    const details = Array.isArray(body?.errors)
      ? body.errors.map((e) => `${e.status || response.status} ${e.code || ''} ${e.title || ''}: ${e.detail || ''}`.trim()).join('\n')
      : `${response.status} ${response.statusText}`;
    throw new Error(`Apple cleanup ${options.method || 'GET'} ${pathname} failed: ${details}`);
  }
  return response.status;
}

const metadataPath = process.argv[2] || 'build/testflight/signing/apple-signing-material.json';
if (!fs.existsSync(metadataPath)) {
  console.log('[AppForge] No ephemeral Apple signing metadata to clean up.');
  process.exit(0);
}

const issuerId = String(process.env.APP_STORE_CONNECT_ISSUER_ID || '').trim();
const keyId = String(process.env.APP_STORE_CONNECT_KEY_ID || '').trim();
const keyPath = String(process.env.APP_STORE_CONNECT_KEY_PATH || '').trim();
if (!issuerId || !keyId || !keyPath || !fs.existsSync(keyPath)) {
  throw new Error('Missing App Store Connect credentials for cleanup');
}
const privateKey = fs.readFileSync(keyPath, 'utf8');
const token = makeToken({ issuerId, keyId, privateKey });
const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));

if (metadata.profileId) {
  await request(token, `/v1/profiles/${encodeURIComponent(metadata.profileId)}`, { method: 'DELETE' });
  console.log(`[AppForge] Deleted ephemeral provisioning profile ${metadata.profileId}.`);
}
if (metadata.certificateId) {
  await request(token, `/v1/certificates/${encodeURIComponent(metadata.certificateId)}`, { method: 'DELETE' });
  console.log(`[AppForge] Revoked ephemeral distribution certificate ${metadata.certificateId}.`);
}
