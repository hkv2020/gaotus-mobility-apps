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

const csrPath = process.argv[2] || 'build/signing-bootstrap/distribution.csr';
const signingPrivateKeyPath = process.argv[3] || 'build/signing-bootstrap/distribution.key';
const outputPath = process.argv[4] || 'build/signing-bootstrap/apple-distribution.enc.json';
const issuerId = String(process.env.APP_STORE_CONNECT_ISSUER_ID || '').trim();
const keyId = String(process.env.APP_STORE_CONNECT_KEY_ID || '').trim();
const apiKeyPath = String(process.env.APP_STORE_CONNECT_KEY_PATH || '').trim();

if (!issuerId || !keyId || !apiKeyPath) throw new Error('Missing App Store Connect issuer, key ID, or API key path');
if (!fs.existsSync(apiKeyPath)) throw new Error(`App Store Connect private key not found: ${apiKeyPath}`);
if (!fs.existsSync(csrPath)) throw new Error(`CSR not found: ${csrPath}`);
if (!fs.existsSync(signingPrivateKeyPath)) throw new Error(`Distribution private key not found: ${signingPrivateKeyPath}`);

const apiPrivateKey = fs.readFileSync(apiKeyPath, 'utf8');
const csrContent = fs.readFileSync(csrPath, 'utf8');
const distributionPrivateKey = fs.readFileSync(signingPrivateKeyPath, 'utf8');
if (!apiPrivateKey.includes('BEGIN PRIVATE KEY')) throw new Error('Invalid App Store Connect .p8 key');
if (!csrContent.includes('BEGIN CERTIFICATE REQUEST')) throw new Error('Invalid CSR content');
if (!distributionPrivateKey.includes('BEGIN PRIVATE KEY')) throw new Error('Invalid distribution private key');

const token = makeToken({ issuerId, keyId, privateKey: apiPrivateKey });
await api(token, '/v1/apps?limit=1');

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
const certificate = certResponse?.data || null;
if (!certificate?.id || !certificate?.attributes?.certificateContent) {
  throw new Error('Apple did not return a usable iOS distribution certificate');
}

const plaintext = Buffer.from(JSON.stringify({
  version: 1,
  createdAt: new Date().toISOString(),
  certificateId: certificate.id,
  certificateType: certificate.attributes.certificateType,
  certificateExpirationDate: certificate.attributes.expirationDate || null,
  certificateContentDerBase64: certificate.attributes.certificateContent,
  distributionPrivateKeyPem: distributionPrivateKey,
}, null, 2));

const encryptionKey = deriveKey(apiPrivateKey, issuerId, keyId);
const iv = crypto.randomBytes(12);
const cipher = crypto.createCipheriv('aes-256-gcm', encryptionKey, iv);
const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
const tag = cipher.getAuthTag();

const envelope = {
  version: 1,
  algorithm: 'AES-256-GCM',
  keyDerivation: 'SHA-256(AppStoreConnectKey+issuer+keyId+context)',
  iv: iv.toString('base64'),
  tag: tag.toString('base64'),
  ciphertext: ciphertext.toString('base64'),
};
fs.mkdirSync(new URL('.', `file://${process.cwd()}/${outputPath}`).pathname, { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(envelope, null, 2) + '\n', { mode: 0o600 });
console.log(`[AppForge] Persistent Apple Distribution identity created and encrypted. Certificate ID: ${certificate.id}`);
console.log(`[AppForge] Encrypted identity written to ${outputPath}; private key was not printed.`);
