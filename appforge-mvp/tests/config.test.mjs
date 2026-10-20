import test from 'node:test';
import assert from 'node:assert/strict';
import { validateClient, capacitorConfigObject } from '../scripts/lib.mjs';

const base = {
  appId: 'ai.gaotus.testapp', appName: 'Test App', mode: 'local', url: null,
  themeColor: '#111827', versionName: '1.2.3', versionCode: 7
};

test('valid local config passes', () => {
  assert.equal(validateClient({ ...base }).appId, base.appId);
});

test('invalid appId fails closed', () => {
  assert.throws(() => validateClient({ ...base, appId: 'bad id' }), /appId/);
});

test('remote config injects server URL and host allowlist', () => {
  const c = { ...base, mode: 'remote', url: 'https://shop.example.com/path' };
  const cap = capacitorConfigObject(validateClient(c));
  assert.equal(cap.server.url, c.url);
  assert.deepEqual(cap.server.allowNavigation, ['shop.example.com', '*.shop.example.com']);
});

test('http remote mode explicitly enables cleartext', () => {
  const c = { ...base, mode: 'remote', url: 'http://dev.example.com' };
  const cap = capacitorConfigObject(validateClient(c));
  assert.equal(cap.server.cleartext, true);
});
