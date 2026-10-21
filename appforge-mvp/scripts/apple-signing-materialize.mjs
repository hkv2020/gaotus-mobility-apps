import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
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
  try { body = text ? JSON.parse(text) : null; } catch { body = { raw: text.slice(0, 1200) }; }
  if (!response.ok) {
    const details = Array.isArray(body?.errors)
      ? body.errors.map((e) => `${e.status || response.status} ${e.code || ''} ${e.title || ''}: ${e.detail || ''}`.trim()).join('\n')
      : `${response.status} ${response.statusText}`;
    throw new Error(`App Store Connect API ${options.method || 'GET'} ${pathname} failed:\n${details}`);
  }
  return body;
}

function deriveKey(apiPrivateKey, issuerId, keyId) {
  return crypto.createHash('sha256')
    .update('gaotus-appforge-persistent-signing-v1\0')
    .update(issuerId)
    .update('\0')
    .update(keyId)
    .update('\0')
    .update(apiPrivateKey)
    .digest();
}

function decryptIdentity(envelope, apiPrivateKey, issuerId, keyId) {
  if (!envelope || envelope.version !== 1 || envelope.algorithm !== 'AES-256-GCM') {
    throw new Error('Unsupported persistent Apple signing identity envelope');
  }
  const key = deriveKey(apiPrivateKey, issuerId, keyId);
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(envelope.iv, 'base64'));
  decipher.setAuthTag(Buffer.from(envelope.tag, 'base64'));
  const plain = Buffer.concat([
    decipher.update(Buffer.from(envelope.ciphertext, 'base64')),
    decipher.final(),
  ]);
  const identity = JSON.parse(plain.toString('utf8'));
  if (!identity?.certificateId || !identity?.certificateContentDerBase64 || !identity?.distributionPrivateKeyPem) {
    throw new Error('Decrypted Apple signing identity is incomplete');
  }
  if (!identity.distributionPrivateKeyPem.includes('BEGIN PRIVATE KEY')) {
    throw new Error('Decrypted Apple signing private key is invalid');
  }
  return identity;
}

const configPath = process.argv[2] || 'clients/runtime-builder.json';
const encryptedIdentityPath = process.argv[3] || 'signing/apple-distribution.enc.json';
const outputDir = process.argv[4] || 'build/testflight/signing';
const config = validateClient(readJSON(configPath));

const issuerId = String(process.env.APP_STORE_CONNECT_ISSUER_ID || '').trim();
const keyId = String(process.env.APP_STORE_CONNECT_KEY_ID || '').trim();
const keyPath = String(process.env.APP_STORE_CONNECT_KEY_PATH || '').trim();
if (!issuerId || !keyId || !keyPath) throw new Error('Missing App Store Connect issuer, key ID, or key path');
if (!fs.existsSync(keyPath)) throw new Error(`App Store Connect private key file not found: ${keyPath}`);
if (!fs.existsSync(encryptedIdentityPath)) throw new Error(`Encrypted Apple distribution identity not found: ${encryptedIdentityPath}`);

const apiPrivateKey = fs.readFileSync(keyPath, 'utf8');
if (!apiPrivateKey.includes('BEGIN PRIVATE KEY')) throw new Error('Invalid App Store Connect .p8 key');
const envelope = JSON.parse(fs.readFileSync(encryptedIdentityPath, 'utf8'));
const identity = decryptIdentity(envelope, apiPrivateKey, issuerId, keyId);
const token = makeToken({ issuerId, keyId, privateKey: apiPrivateKey });

const certResponse = await api(token, `/v1/certificates/${encodeURIComponent(identity.certificateId)}`);
const cert = certResponse?.data || null;
if (!cert?.id || cert.id !== identity.certificateId) throw new Error('Persistent Apple Distribution certificate could not be verified');
const expires = cert.attributes?.expirationDate ? Date.parse(cert.attributes.expirationDate) : NaN;
if (Number.isFinite(expires) && expires <= Date.now() + 7 * 86400000) {
  throw new Error(`Persistent Apple Distribution certificate expires too soon: ${cert.attributes.expirationDate}`);
}

const bundleQuery = new URLSearchParams({ 'filter[identifier]': config.appId, limit: '10' });
const bundleResponse = await api(token, `/v1/bundleIds?${bundleQuery.toString()}`);
const bundle = Array.isArray(bundleResponse?.data) ? bundleResponse.data[0] : null;
if (!bundle?.id) throw new Error(`Bundle ID ${config.appId} is not registered`);

const profileName = `Gaotus AppForge ${config.appId} ${Date.now()}`.slice(0, 120);
const profileResponse = await api(token, '/v1/profiles', {
  method: 'POST',
  body: JSON.stringify({
    data: {
      type: 'profiles',
      attributes: {
        name: profileName,
        profileType: 'IOS_APP_STORE',
      },
      relationships: {
        bundleId: { data: { type: 'bundleIds', id: bundle.id } },
        certificates: { data: [{ type: 'certificates', id: identity.certificateId }] },
      },
    },
  }),
});
const profile = profileResponse?.data || null;
if (!profile?.id || !profile?.attributes?.profileContent || !profile?.attributes?.uuid) {
  throw new Error('Apple did not return a usable App Store provisioning profile');
}

fs.mkdirSync(outputDir, { recursive: true });
fs.writeFileSync(path.join(outputDir, 'distribution.key'), identity.distributionPrivateKeyPem, { mode: 0o600 });
fs.writeFileSync(path.join(outputDir, 'distribution.cer'), Buffer.from(identity.certificateContentDerBase64, 'base64'));
fs.writeFileSync(path.join(outputDir, 'appstore.mobileprovision'), Buffer.from(profile.attributes.profileContent, 'base64'));
const metadata = {
  createdAt: new Date().toISOString(),
  persistentCertificate: true,
  bundleIdentifier: config.appId,
  bundleIdResourceId: bundle.id,
  certificateId: identity.certificateId,
  certificateType: cert.attributes?.certificateType || identity.certificateType || 'IOS_DISTRIBUTION',
  certificateExpirationDate: cert.attributes?.expirationDate || identity.certificateExpirationDate || null,
  profileId: profile.id,
  profileUuid: profile.attributes.uuid,
  profileName: profile.attributes.name,
  profileType: profile.attributes.profileType,
  profileExpirationDate: profile.attributes.expirationDate || null,
};
fs.writeFileSync(path.join(outputDir, 'apple-signing-material.json'), JSON.stringify(metadata, null, 2) + '\n');
console.log(`[AppForge] Reused persistent Apple Distribution certificate ${identity.certificateId}.`);
console.log(`[AppForge] Created per-app App Store profile ${profile.id} for ${config.appId}.`);
