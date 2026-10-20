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
  for (const key of keys) {
    if (key in object && !isBool(object[key])) errors.push(`${prefix}.${key} must be boolean`);
  }
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

  const settings = c?.appSettings || {};
  if (settings.orientation !== undefined && !['portrait', 'landscape', 'both'].includes(settings.orientation)) errors.push('appSettings.orientation invalid');
  for (const key of ['status_bar_color', 'navigation_bar_color']) {
    if (settings[key] !== undefined && !isColor(settings[key])) errors.push(`appSettings.${key} must be #RRGGBB`);
  }

  const links = c?.linkHandling || {};
  if (links.external_mode !== undefined && !['external', 'in_app'].includes(links.external_mode)) errors.push('linkHandling.external_mode invalid');
  if (links.custom_scheme && !/^[A-Za-z][A-Za-z0-9+.-]*$/.test(String(links.custom_scheme))) errors.push('linkHandling.custom_scheme invalid');

  const overrides = c?.overrides || {};
  if (String(overrides.custom_css || '').length > 100000) errors.push('overrides.custom_css too large');
  if (String(overrides.custom_js || '').length > 100000) errors.push('overrides.custom_js too large');
  if (String(overrides.custom_headers || '').length > 20000) errors.push('overrides.custom_headers too large');

  const ui = c?.uiNavigation || {};
  pushBoolErrors(errors, ui, ['header_enabled', 'bottom_nav_enabled', 'floating_button_enabled'], 'uiNavigation');
  if (ui.header_background !== undefined && !isColor(ui.header_background)) errors.push('uiNavigation.header_background must be #RRGGBB');
  if (ui.header_text !== undefined && !isColor(ui.header_text)) errors.push('uiNavigation.header_text must be #RRGGBB');
  if (ui.bottom_nav_items !== undefined) {
    if (!Array.isArray(ui.bottom_nav_items)) errors.push('uiNavigation.bottom_nav_items must be array');
    else {
      if (ui.bottom_nav_items.length > 5) errors.push('uiNavigation.bottom_nav_items max 5');
      ui.bottom_nav_items.forEach((item, index) => {
        if (!isObj(item) || !String(item.label || '').trim() || !String(item.url || '').trim()) errors.push(`uiNavigation.bottom_nav_items[${index}] requires label and url`);
      });
    }
  }

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
      if (environment.length > 20) errors.push('environment max 20 entries');
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

export function featurePlan(c) {
  validateClient(c);
  const settings = c.appSettings || {};
  const ui = c.uiNavigation || {};
  const notifications = c.notifications || {};
  const security = c.security || {};
  const device = c.deviceHardware || {};
  return {
    remote: c.mode === 'remote',
    host: c.mode === 'remote' ? new URL(c.url).hostname : '',
    pullRefresh: settings.pull_to_refresh === true,
    pageLoader: settings.page_loader === true,
    nativeUi: ui.header_enabled === true || ui.bottom_nav_enabled === true || ui.floating_button_enabled === true || settings.pull_to_refresh === true || settings.page_loader === true,
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
