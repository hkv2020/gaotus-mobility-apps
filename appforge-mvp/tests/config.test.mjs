import test from 'node:test';
import assert from 'node:assert/strict';
import { validateClient, capacitorConfigObject, featurePlan } from '../scripts/lib.mjs';

const base = {
  appId: 'ai.gaotus.testapp',
  appName: 'Test App',
  mode: 'local',
  url: null,
  themeColor: '#111827',
  accentColor: '#fbbf24',
  versionName: '1.2.3',
  versionCode: 7,
};

test('valid local config passes', () => {
  assert.equal(validateClient({ ...base }).appId, base.appId);
});

test('invalid appId fails closed', () => {
  assert.throws(() => validateClient({ ...base, appId: 'bad id' }), /appId/);
});

test('remote https config injects server URL and host allowlist', () => {
  const c = { ...base, mode: 'remote', url: 'https://shop.example.com/path' };
  const cap = capacitorConfigObject(validateClient(c));
  assert.equal(cap.server.url, c.url);
  assert.deepEqual(cap.server.allowNavigation, ['shop.example.com', '*.shop.example.com']);
});

test('http remote mode fails closed unless explicitly allowed', () => {
  const bad = { ...base, mode: 'remote', url: 'http://dev.example.com' };
  assert.throws(() => validateClient(bad), /allow_http/);
  const good = { ...bad, linkHandling: { allow_http: true } };
  const cap = capacitorConfigObject(validateClient(good));
  assert.equal(cap.server.cleartext, true);
});

test('invalid advanced booleans and orientation fail closed', () => {
  assert.throws(() => validateClient({ ...base, appSettings: { pull_to_refresh: 'yes', orientation: 'diagonal' } }), /pull_to_refresh|orientation/);
});

test('bottom navigation supports at most five valid items', () => {
  const items = Array.from({ length: 6 }, (_, i) => ({ label: `Item ${i}`, url: `/${i}` }));
  assert.throws(() => validateClient({ ...base, uiNavigation: { bottom_nav_items: items } }), /max 5/);
});

test('notifications fail closed without matching firebase client config', () => {
  assert.throws(() => validateClient({ ...base, notifications: { provider: 'firebase' } }), /firebaseGoogleServicesB64/);
});

test('environment keys must be uppercase and unique', () => {
  assert.throws(() => validateClient({ ...base, environment: [{ key: 'bad-key', value: 'x' }] }), /environment/);
  assert.throws(() => validateClient({ ...base, environment: [{ key: 'API_URL', value: 'a' }, { key: 'API_URL', value: 'b' }] }), /duplicate/);
});

test('feature plan reflects conditional native dependencies', () => {
  const c = validateClient({
    ...base,
    mode: 'remote',
    url: 'https://example.com/',
    appSettings: { pull_to_refresh: true, page_loader: false },
    uiNavigation: { header_enabled: false, bottom_nav_enabled: true, floating_button_enabled: false, bottom_nav_items: [{ label: 'Home', url: '/' }] },
    security: { biometric_lock: true, prevent_screenshots: false },
    deviceHardware: { keep_screen_on: true },
    notifications: { provider: 'none' },
  });
  const plan = featurePlan(c);
  assert.equal(plan.pullRefresh, true);
  assert.equal(plan.nativeUi, true);
  assert.equal(plan.biometric, true);
  assert.equal(plan.keepAwake, true);
  assert.equal(plan.notifications, 'none');
});
