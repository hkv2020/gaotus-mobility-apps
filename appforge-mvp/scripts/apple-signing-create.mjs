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

const configPath = process.argv[2] || 'clients/runtime-testflight.json';
const csrPath = process.argv[3] || 'build/testflight/signing/distribution.csr';
const outputDir = process.argv[4] || 'build/testflight/signing';
const config = validateClient(readJSON(configPath));

const issuerId = String(process.env.APP_STORE_CONNECT_ISSUER_ID || '').trim();
const keyId = String(process.env.APP_STORE_CONNECT_KEY_ID || '').trim();
const keyPath = String(process.env.APP_STORE_CONNECT_KEY_PATH || '').trim();
if (!issuerId || !keyId || !keyPath) throw new Error('Missing App Store Connect issuer, key ID, or key path');
if (!fs.existsSync(keyPath)) throw new Error(`App Store Connect private key file not found: ${keyPath}`);
if (!fs.existsSync(csrPath)) throw new Error(`CSR not found: ${csrPath}`);

const apiPrivateKey = fs.readFileSync(keyPath, 'utf8');
const csrContent = fs.readFileSync(csrPath, 'utf8');
if (!apiPrivateKey.includes('BEGIN PRIVATE KEY')) throw new Error('Invalid App Store Connect .p8 key');
if (!csrContent.includes('BEGIN CERTIFICATE REQUEST')) throw new Error('Invalid CSR content');

const token = makeToken({ issuerId, keyId, privateKey: apiPrivateKey });
await api(token, '/v1/apps?limit=1');

const bundleQuery = new URLSearchParams({ 'filter[identifier]': config.appId, limit: '10' });
const bundleResponse = await api(token, `/v1/bundleIds?${bundleQuery.toString()}`);
const bundle = Array.isArray(bundleResponse?.data) ? bundleResponse.data[0] : null;
if (!bundle?.id) throw new Error(`Bundle ID ${config.appId} is not registered`);

fs.mkdirSync(outputDir, { recursive: true });
let certificate = null;
let profile = null;
try {
  const certResponse = await api(token, '/v1/certificates', {
    method: 'POST',
    body: JSON.stringify({
      data: {
        type: 'certificates',
        attributes: {
          certificateType: 'IOS_DISTRIBUTION',
          csrContent,
        },
      },
    }),
  });
  certificate = certResponse?.data || null;
  if (!certificate?.id || !certificate?.attributes?.certificateContent) {
    throw new Error('Apple did not return a usable iOS distribution certificate');
  }

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
          bundleId: {
            data: { type: 'bundleIds', id: bundle.id },
          },
          certificates: {
            data: [{ type: 'certificates', id: certificate.id }],
          },
        },
      },
    }),
  });
  profile = profileResponse?.data || null;
  if (!profile?.id || !profile?.attributes?.profileContent || !profile?.attributes?.uuid) {
    throw new Error('Apple did not return a usable App Store provisioning profile');
  }

  fs.writeFileSync(path.join(outputDir, 'distribution.cer'), Buffer.from(certificate.attributes.certificateContent, 'base64'));
  fs.writeFileSync(path.join(outputDir, 'appstore.mobileprovision'), Buffer.from(profile.attributes.profileContent, 'base64'));
  const metadata = {
    createdAt: new Date().toISOString(),
    bundleIdentifier: config.appId,
    bundleIdResourceId: bundle.id,
    certificateId: certificate.id,
    certificateType: certificate.attributes.certificateType,
    certificateExpirationDate: certificate.attributes.expirationDate || null,
    profileId: profile.id,
    profileUuid: profile.attributes.uuid,
    profileName: profile.attributes.name,
    profileType: profile.attributes.profileType,
    profileExpirationDate: profile.attributes.expirationDate || null,
  };
  fs.writeFileSync(path.join(outputDir, 'apple-signing-material.json'), JSON.stringify(metadata, null, 2) + '\n');
  console.log(`[AppForge] Created ephemeral Apple Distribution certificate ${certificate.id} and App Store profile ${profile.id}.`);
  console.log(`[AppForge] Provisioning profile: ${metadata.profileName} (${metadata.profileUuid})`);
} catch (error) {
  if (profile?.id) {
    try { await api(token, `/v1/profiles/${profile.id}`, { method: 'DELETE' }); } catch {}
  }
  if (certificate?.id) {
    try {
      await api(token, `/v1/certificates/${certificate.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ data: { type: 'certificates', id: certificate.id, attributes: { activated: false } } }),
      });
    } catch {}
  }
  throw error;
}
