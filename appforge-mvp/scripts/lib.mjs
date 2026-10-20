import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const readJSON = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));

const isBool = (value) => typeof value === 'boolean';
const isColor = (value) => /^#[0-9a-fA-F]{6}$/.test(String(value || ''));
const isObj = (value) => value && typeof value === 'object' && !Array.isArray(value);
const pushBoolErrors = (errors, object, keys, prefix) => {
  if (!isObj(object)) return;
  for (const key of keys) if (key in object && !isBool(object[key])) errors.push(`${prefix}.${key} must be boolean`);
};
const validUrlish = (value) => {
  const s = String(value || '').trim();
  if (!s) return true;
  if (s.startsWith('/')) return true;
  if (/^\{\{ENV[.:][A-Z][A-Z0-9_]*\}\}/.test(s)) return true;
  try { const u = new URL(s); return ['http:', 'https:'].includes(u.protocol); } catch { return false; }
};
const integerRange = (errors, value, min, max, label) => {
  if (value === undefined) return;
  if (!Number.isInteger(value) || value < min || value > max) errors.push(`${label} must be integer ${min}-${max}`);
};
const textLimit = (errors, value, max, label) => {
  if (value !== undefined && String(value).length > max) errors.push(`${label} must be <= ${max} characters`);
};

export function validateClient(c) {
  const errors = [];
  if (!isObj(c)) errors.push('config object required');

  const appId = String(c?.appId || '');
  const appName = String(c?.appName || '').trim();
  const mode = c?.mode;
  if (!/^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*){2,}$/.test(appId)) errors.push('invalid appId');
  if (!appName) errors.push('appName required');
  if (appName.length > 80) errors.push('appName must be <= 80 characters');
  if (!['local', 'remote'].includes(mode)) errors.push('mode must be local or remote');

  if (mode === 'remote') {
    try {
      const remoteUrl = new URL(c.url);
      if (!['https:', 'http:'].includes(remoteUrl.protocol)) errors.push('remote url must use http/https');
      if (!remoteUrl.hostname) errors.push('remote url hostname required');
      if (remoteUrl.username || remoteUrl.password) errors.push('remote url must not contain credentials');
      if (remoteUrl.protocol === 'http:' && c?.linkHandling?.allow_http !== true) errors.push('http remote url requires linkHandling.allow_http=true');
    } catch {
      errors.push('valid remote url required');
    }
  }

  if (!isColor(c?.themeColor)) errors.push('themeColor must be #RRGGBB');
  if (c?.accentColor !== undefined && !isColor(c.accentColor)) errors.push('accentColor must be #RRGGBB');
  if (!Number.isInteger(c?.versionCode) || c.versionCode < 1) errors.push('versionCode >= 1 required');
  if (!/^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/.test(String(c?.versionName || ''))) errors.push('versionName must be semantic x.y.z');

  pushBoolErrors(errors, c?.features, ['share', 'haptics', 'openExternal', 'deviceInfo', 'camera', 'location'], 'features');
  pushBoolErrors(errors, c?.permissions, ['camera', 'location', 'microphone', 'storage', 'vibration', 'play_services'], 'permissions');
  pushBoolErrors(errors, c?.appSettings, ['fullscreen', 'pinch_zoom', 'disable_cache', 'kiosk_mode', 'scroll_bounce', 'pull_to_refresh', 'page_loader', 'confirm_exit'], 'appSettings');
  pushBoolErrors(errors, c?.linkHandling, ['allow_subdomains', 'allow_http', 'deep_linking'], 'linkHandling');
  pushBoolErrors(errors, c?.security, ['prevent_screenshots', 'biometric_lock'], 'security');
  pushBoolErrors(errors, c?.communication, ['native_share', 'external_phone_email'], 'communication');
  pushBoolErrors(errors, c?.deviceHardware, ['keep_screen_on'], 'deviceHardware');
  pushBoolErrors(errors, c?.localisation, ['rtl'], 'localisation');
  pushBoolErrors(errors, c?.pdfViewer, ['enabled'], 'pdfViewer');
  pushBoolErrors(errors, c?.backExit, ['disable_back_button'], 'backExit');

  const settings = c?.appSettings || {};
  if (settings.orientation !== undefined && !['portrait', 'landscape', 'both'].includes(settings.orientation)) errors.push('appSettings.orientation invalid');
  for (const key of ['status_bar_color', 'navigation_bar_color']) if (settings[key] !== undefined && !isColor(settings[key])) errors.push(`appSettings.${key} must be #RRGGBB`);

  const links = c?.linkHandling || {};
  if (links.external_mode !== undefined && !['external', 'in_app'].includes(links.external_mode)) errors.push('linkHandling.external_mode invalid');
  if (links.custom_scheme && !/^[A-Za-z][A-Za-z0-9+.-]*$/.test(String(links.custom_scheme))) errors.push('linkHandling.custom_scheme invalid');

  const overrides = c?.overrides || {};
  if (String(overrides.custom_css || '').length > 100000) errors.push('overrides.custom_css too large');
  if (String(overrides.custom_js || '').length > 100000) errors.push('overrides.custom_js too large');
  if (String(overrides.custom_headers || '').length > 20000) errors.push('overrides.custom_headers too large');

  const ui = c?.uiNavigation || {};
  pushBoolErrors(errors, ui, [
    'header_enabled', 'bottom_nav_enabled', 'floating_button_enabled', 'sidebar_enabled',
    'offline_enabled', 'error_enabled'
  ], 'uiNavigation');
  const colorKeys = [
    'header_background', 'header_text', 'bottom_nav_default_color', 'bottom_nav_active_color',
    'bottom_nav_background_color', 'floating_button_background', 'floating_button_text',
    'sidebar_background', 'sidebar_text', 'offline_background', 'offline_title_color',
    'offline_message_color', 'offline_button_background', 'offline_button_text_color',
    'error_background', 'error_title_color', 'error_message_color', 'error_button_background',
    'error_button_text_color', 'page_loader_color', 'page_loader_background', 'pull_refresh_color'
  ];
  for (const key of colorKeys) if (ui[key] !== undefined && !isColor(ui[key])) errors.push(`uiNavigation.${key} must be #RRGGBB`);
  if (ui.header_template !== undefined && !['simple_dark','side_logo_dark','simple_light','floating_dark','right_logo_dark','logo_search'].includes(ui.header_template)) errors.push('uiNavigation.header_template invalid');
  if (ui.floating_button_position !== undefined && !['left','right'].includes(ui.floating_button_position)) errors.push('uiNavigation.floating_button_position invalid');
  if (ui.floating_button_shape !== undefined && !['circular','square'].includes(ui.floating_button_shape)) errors.push('uiNavigation.floating_button_shape invalid');
  if (ui.sidebar_template !== undefined && !['vertical_cards','submenus','cards','single'].includes(ui.sidebar_template)) errors.push('uiNavigation.sidebar_template invalid');
  if (ui.page_loader_type !== undefined && !['progress','circular','lottie'].includes(ui.page_loader_type)) errors.push('uiNavigation.page_loader_type invalid');
  textLimit(errors, ui.header_title, 80, 'uiNavigation.header_title');
  textLimit(errors, ui.header_search_url, 500, 'uiNavigation.header_search_url');
  textLimit(errors, ui.floating_button_label, 40, 'uiNavigation.floating_button_label');
  textLimit(errors, ui.floating_button_url, 1000, 'uiNavigation.floating_button_url');
  textLimit(errors, ui.floating_button_icon, 40, 'uiNavigation.floating_button_icon');
  integerRange(errors, ui.offline_title_size, 12, 64, 'uiNavigation.offline_title_size');
  integerRange(errors, ui.offline_message_size, 10, 32, 'uiNavigation.offline_message_size');
  integerRange(errors, ui.offline_button_margin, 0, 50, 'uiNavigation.offline_button_margin');
  integerRange(errors, ui.error_title_size, 12, 64, 'uiNavigation.error_title_size');
  integerRange(errors, ui.error_message_size, 10, 32, 'uiNavigation.error_message_size');
  integerRange(errors, ui.error_button_margin, 0, 50, 'uiNavigation.error_button_margin');
  for (const [key, value] of [['offline_title_weight', ui.offline_title_weight],['offline_message_weight',ui.offline_message_weight],['error_title_weight',ui.error_title_weight],['error_message_weight',ui.error_message_weight]]) {
    if (value !== undefined && ![400,600,700].includes(Number(value))) errors.push(`uiNavigation.${key} invalid`);
  }
  for (const key of ['floating_button_url','offline_image_url','error_image_url','page_loader_lottie_url','header_search_url']) if (ui[key] && !validUrlish(ui[key]) && key !== 'header_search_url') errors.push(`uiNavigation.${key} invalid`);

  const validateNavItems = (items, max, label) => {
    if (items === undefined) return;
    if (!Array.isArray(items)) return errors.push(`${label} must be array`);
    if (items.length > max) errors.push(`${label} max ${max}`);
    items.forEach((item, index) => {
      if (!isObj(item) || !String(item.label || '').trim() || !String(item.url || '').trim()) return errors.push(`${label}[${index}] requires label and url`);
      if (!validUrlish(item.url)) errors.push(`${label}[${index}].url invalid`);
      textLimit(errors, item.label, 40, `${label}[${index}].label`);
      textLimit(errors, item.icon, 40, `${label}[${index}].icon`);
    });
  };
  validateNavItems(ui.bottom_nav_items, 5, 'uiNavigation.bottom_nav_items');
  validateNavItems(ui.sidebar_items, 12, 'uiNavigation.sidebar_items');

  const back = c?.backExit || {};
  if (back.mode !== undefined && !['confirm','immediate'].includes(back.mode)) errors.push('backExit.mode invalid');
  textLimit(errors, back.message, 100, 'backExit.message');
  for (const listKey of ['exit_pages','disable_back_pages']) {
    if (back[listKey] !== undefined) {
      if (!Array.isArray(back[listKey])) errors.push(`backExit.${listKey} must be array`);
      else if (back[listKey].length > 30) errors.push(`backExit.${listKey} max 30`);
      else back[listKey].forEach((value, index) => { if (!validUrlish(value)) errors.push(`backExit.${listKey}[${index}] invalid`); });
    }
  }

  const pdf = c?.pdfViewer || {};
  if (pdf.mode !== undefined && !['in_app','external'].includes(pdf.mode)) errors.push('pdfViewer.mode invalid');

  const notifications = c?.notifications || {};
  const provider = notifications.provider || 'none';
  if (!['none', 'firebase', 'onesignal'].includes(provider)) errors.push('notifications.provider invalid');
  if (provider === 'onesignal' && !String(notifications.onesignal_app_id || '').trim()) errors.push('OneSignal provider requires notifications.onesignal_app_id');
  if (provider !== 'none') {
    const encoded = String(c?.firebaseGoogleServicesB64 || '');
    if (!encoded) errors.push(`${provider} notifications require firebaseGoogleServicesB64`);
    else {
      try {
        const raw = Buffer.from(encoded, 'base64').toString('utf8');
        const firebase = JSON.parse(raw);
        const packages = (firebase.client || []).map((x) => x?.client_info?.android_client_info?.package_name).filter(Boolean);
        if (!packages.includes(appId)) errors.push(`google-services.json does not match ${appId}`);
      } catch {
        errors.push('firebaseGoogleServicesB64 must contain valid google-services.json');
      }
    }
  }

  const environment = c?.environment;
  if (environment !== undefined) {
    if (!Array.isArray(environment)) errors.push('environment must be array');
    else {
      if (environment.length > 40) errors.push('environment max 40 entries');
      const seen = new Set();
      environment.forEach((row, index) => {
        if (!isObj(row)) return errors.push(`environment[${index}] must be object`);
        const key = String(row.key || '').trim();
        if (!/^[A-Z][A-Z0-9_]*$/.test(key)) errors.push(`environment[${index}].key invalid`);
        if (seen.has(key)) errors.push(`environment duplicate key ${key}`);
        seen.add(key);
        if (String(row.value ?? '').length > 4000) errors.push(`environment[${index}].value too large`);
      });
    }
  }

  if (errors.length) throw new Error(errors.join('\n'));
  return c;
}

export function environmentMap(c) {
  validateClient(c);
  const map = {};
  if (c.mode === 'remote' && c.url) map.BASE_URL = String(c.url).replace(/\/+$/, '');
  else map.BASE_URL = '';
  for (const row of Array.isArray(c.environment) ? c.environment : []) {
    const key = String(row?.key || '').trim().toUpperCase();
    if (!key || key === 'BASE_URL') continue;
    map[key] = String(row?.value ?? '');
  }
  const token = /\{\{ENV(?:\.|:)([A-Z][A-Z0-9_]*)\}\}/g;
  for (let pass = 0; pass < 6; pass++) {
    let changed = false;
    for (const key of Object.keys(map)) {
      const next = String(map[key]).replace(token, (_, name) => Object.prototype.hasOwnProperty.call(map, name) ? map[name] : `{{ENV.${name}}}`);
      if (next !== map[key]) { map[key] = next; changed = true; }
    }
    if (!changed) break;
  }
  if (map.BASE_URL) {
    for (const key of Object.keys(map)) {
      if (key !== 'BASE_URL' && String(map[key]).startsWith('/')) map[key] = map.BASE_URL + String(map[key]);
    }
  }
  return map;
}

export function resolveEnvironmentTokens(c) {
  const source = structuredClone(validateClient(c));
  const env = environmentMap(source);
  const token = /\{\{ENV(?:\.|:)([A-Z][A-Z0-9_]*)\}\}/g;
  const walk = (value, key = '') => {
    if (key === 'firebaseGoogleServicesB64') return value;
    if (typeof value === 'string') return value.replace(token, (_, name) => Object.prototype.hasOwnProperty.call(env, name) ? env[name] : `{{ENV.${name}}}`);
    if (Array.isArray(value)) return value.map((v) => walk(v));
    if (isObj(value)) {
      const out = {};
      for (const [k, v] of Object.entries(value)) out[k] = walk(v, k);
      return out;
    }
    return value;
  };
  const resolved = walk(source);
  resolved.environment = Object.entries(env).map(([key, value]) => ({ key, value }));
  return resolved;
}

export function featurePlan(c) {
  validateClient(c);
  const settings = c.appSettings || {};
  const ui = c.uiNavigation || {};
  const notifications = c.notifications || {};
  const security = c.security || {};
  const device = c.deviceHardware || {};
  const pdf = c.pdfViewer || {};
  const back = c.backExit || {};
  const pageLoaderType = ['progress','circular','lottie'].includes(ui.page_loader_type) ? ui.page_loader_type : 'circular';
  return {
    remote: c.mode === 'remote',
    host: c.mode === 'remote' ? new URL(c.url).hostname : '',
    pullRefresh: settings.pull_to_refresh === true,
    pageLoader: settings.page_loader === true,
    pageLoaderType,
    lottieLoader: settings.page_loader === true && pageLoaderType === 'lottie',
    header: ui.header_enabled === true,
    bottomNav: ui.bottom_nav_enabled === true,
    floatingButton: ui.floating_button_enabled === true,
    sidebar: ui.sidebar_enabled === true,
    nativeUi: ui.header_enabled === true || ui.bottom_nav_enabled === true || ui.floating_button_enabled === true || ui.sidebar_enabled === true || settings.pull_to_refresh === true || settings.page_loader === true,
    offlineScreen: ui.offline_enabled !== false,
    errorScreen: ui.error_enabled !== false,
    pdfViewer: pdf.enabled === true,
    pdfViewerMode: pdf.mode === 'external' ? 'external' : 'in_app',
    backExitMode: back.mode === 'immediate' ? 'immediate' : 'confirm',
    disableBack: back.disable_back_button === true,
    notifications: ['firebase', 'onesignal'].includes(notifications.provider) ? notifications.provider : 'none',
    biometric: security.biometric_lock === true,
    secureWindow: security.prevent_screenshots === true,
    keepAwake: device.keep_screen_on === true,
    deepLinking: c.linkHandling?.deep_linking === true,
    customScheme: String(c.linkHandling?.custom_scheme || ''),
  };
}

export function capacitorConfigObject(c) {
  const x = { appId: c.appId, appName: c.appName, webDir: 'www', backgroundColor: c.themeColor, server: { errorPath: 'offline.html' } };
  if (c.mode === 'remote') {
    const u = new URL(c.url);
    x.server.url = c.url;
    x.server.allowNavigation = [u.hostname, `*.${u.hostname}`];
    if (u.protocol === 'http:') x.server.cleartext = true;
  }
  return x;
}

export const tsConfigSource = (c) => `import type { CapacitorConfig } from '@capacitor/cli';\nconst config: CapacitorConfig = ${JSON.stringify(c, null, 2)};\nexport default config;\n`;
