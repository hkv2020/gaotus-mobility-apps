import test from 'node:test';
import assert from 'node:assert/strict';
import { validateClient, capacitorConfigObject, featurePlan, environmentMap, resolveEnvironmentTokens } from '../scripts/lib.mjs';

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

test('valid local config passes', () => assert.equal(validateClient({ ...base }).appId, base.appId));
test('invalid appId fails closed', () => assert.throws(() => validateClient({ ...base, appId: 'bad id' }), /appId/));
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
  assert.equal(capacitorConfigObject(validateClient(good)).server.cleartext, true);
});
test('invalid advanced booleans and orientation fail closed', () => assert.throws(() => validateClient({ ...base, appSettings: { pull_to_refresh: 'yes', orientation: 'diagonal' } }), /pull_to_refresh|orientation/));
test('bottom navigation supports at most five valid items', () => {
  const items = Array.from({ length: 6 }, (_, i) => ({ label: `Item ${i}`, url: `/${i}` }));
  assert.throws(() => validateClient({ ...base, uiNavigation: { bottom_nav_items: items } }), /max 5/);
});
test('sidebar supports at most twelve items', () => {
  const items = Array.from({ length: 13 }, (_, i) => ({ label: `Item ${i}`, url: `/${i}` }));
  assert.throws(() => validateClient({ ...base, uiNavigation: { sidebar_items: items } }), /max 12/);
});
test('navigation templates and colours fail closed on invalid values', () => {
  assert.throws(() => validateClient({ ...base, uiNavigation: { header_template: 'bad', page_loader_type: 'matrix', bottom_nav_active_color: 'red' } }), /header_template|page_loader_type|bottom_nav_active_color/);
});
test('notifications fail closed without matching firebase client config', () => assert.throws(() => validateClient({ ...base, notifications: { provider: 'firebase' } }), /firebaseGoogleServicesB64/));
test('environment keys must be uppercase and unique', () => {
  assert.throws(() => validateClient({ ...base, environment: [{ key: 'bad-key', value: 'x' }] }), /environment/);
  assert.throws(() => validateClient({ ...base, environment: [{ key: 'API_URL', value: 'a' }, { key: 'API_URL', value: 'b' }] }), /duplicate/);
});
test('environment resolver provides BASE_URL and resolves navigation tokens', () => {
  const raw = validateClient({
    ...base, mode: 'remote', url: 'https://example.com/app/',
    environment: [{ key: 'ACCOUNT_PATH', value: '/account' }],
    uiNavigation: { bottom_nav_items: [{ label: 'Account', url: '{{ENV.ACCOUNT_PATH}}', icon: 'user' }] },
  });
  const map = environmentMap(raw);
  assert.equal(map.BASE_URL, 'https://example.com/app');
  assert.equal(map.ACCOUNT_PATH, 'https://example.com/app/account');
  const resolved = resolveEnvironmentTokens(raw);
  assert.equal(resolved.uiNavigation.bottom_nav_items[0].url, 'https://example.com/app/account');
  assert.equal(resolved.environment[0].key, 'BASE_URL');
});
test('back/exit and pdf viewer validate', () => {
  const c = validateClient({ ...base, backExit: { disable_back_button: true, mode: 'confirm', message: 'Press again', exit_pages: ['/'], disable_back_pages: ['/checkout'] }, pdfViewer: { enabled: true, mode: 'in_app' } });
  assert.equal(c.backExit.mode, 'confirm');
  assert.equal(c.pdfViewer.enabled, true);
});
test('feature plan reflects conditional native dependencies', () => {
  const c = validateClient({
    ...base,
    mode: 'remote',
    url: 'https://example.com/',
    appSettings: { pull_to_refresh: true, page_loader: true },
    uiNavigation: {
      header_enabled: true, header_template: 'logo_search', bottom_nav_enabled: true, floating_button_enabled: true,
      floating_button_url: '/contact', sidebar_enabled: true, page_loader_type: 'lottie',
      bottom_nav_items: [{ label: 'Home', url: '/' }], sidebar_items: [{ label: 'Home', url: '/' }]
    },
    backExit: { disable_back_button: false, mode: 'confirm', exit_pages: ['/'] },
    pdfViewer: { enabled: true, mode: 'in_app' },
    security: { biometric_lock: true, prevent_screenshots: false },
    deviceHardware: { keep_screen_on: true },
    notifications: { provider: 'none' },
  });
  const plan = featurePlan(c);
  assert.equal(plan.pullRefresh, true);
  assert.equal(plan.nativeUi, true);
  assert.equal(plan.sidebar, true);
  assert.equal(plan.lottieLoader, true);
  assert.equal(plan.pdfViewer, true);
  assert.equal(plan.biometric, true);
  assert.equal(plan.keepAwake, true);
  assert.equal(plan.notifications, 'none');
});
