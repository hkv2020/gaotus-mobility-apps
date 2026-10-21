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

async function api(token, pathname, options = {}) {
  const response = await fetch(`https://api.appstoreconnect.apple.com${pathname}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    },
  });
  if (response.status === 204 || response.status === 404) return null;
  const text = await response.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = { raw: text.slice(0, 800) }; }
  if (!response.ok) throw new Error(`App Store Connect cleanup failed: ${response.status} ${response.statusText}`);
  return body;
}

const metadataPath = process.argv[2] || 'build/testflight/signing/apple-signing-material.json';
if (!fs.existsSync(metadataPath)) process.exit(0);
const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
const profileId = String(metadata.profileId || '').trim();
if (!profileId) process.exit(0);

const issuerId = String(process.env.APP_STORE_CONNECT_ISSUER_ID || '').trim();
const keyId = String(process.env.APP_STORE_CONNECT_KEY_ID || '').trim();
const keyPath = String(process.env.APP_STORE_CONNECT_KEY_PATH || '').trim();
if (!issuerId || !keyId || !keyPath || !fs.existsSync(keyPath)) throw new Error('Apple API credentials unavailable for profile cleanup');
const privateKey = fs.readFileSync(keyPath, 'utf8');
const token = makeToken({ issuerId, keyId, privateKey });
await api(token, `/v1/profiles/${encodeURIComponent(profileId)}`, { method: 'DELETE' });
console.log(`[AppForge] Deleted temporary provisioning profile ${profileId}. Persistent distribution certificate was retained.`);
