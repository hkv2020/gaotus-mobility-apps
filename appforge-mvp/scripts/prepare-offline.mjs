import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const ui = client.uiNavigation || {};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
const color = (v, fallback) => /^#[0-9a-fA-F]{6}$/.test(String(v || '')) ? String(v) : fallback;
const clamp = (v, min, max, fallback) => Number.isFinite(Number(v)) ? Math.max(min, Math.min(max, Number(v))) : fallback;
const weight = (v, fallback) => [400,600,700].includes(Number(v)) ? Number(v) : fallback;

async function imageData(url) {
  const value = String(url || '').trim();
  if (!/^https:\/\//i.test(value)) return '';
  try {
    const parsed = new URL(value);
    const host = parsed.hostname.toLowerCase();
    if (!host || host === 'localhost' || host === '0.0.0.0' || host === '::1' || /^127\./.test(host) || /^10\./.test(host) || /^192\.168\./.test(host) || /^169\.254\./.test(host) || /^172\.(1[6-9]|2\d|3[01])\./.test(host)) return '';
    const response = await fetch(value, { signal: AbortSignal.timeout(12000), redirect: 'follow' });
    if (!response.ok) return '';
    const type = String(response.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
    if (!type.startsWith('image/')) return '';
    const body = Buffer.from(await response.arrayBuffer());
    if (body.length < 1 || body.length > 5 * 1024 * 1024) return '';
    return `data:${type};base64,${body.toString('base64')}`;
  } catch {
    return '';
  }
}

function screenHtml(kind, cfg, embeddedImage) {
  const theme = color(cfg.background, kind === 'offline' ? client.themeColor : '#ffffff');
  const title = esc(cfg.title);
  const message = esc(cfg.message);
  const titleColor = color(cfg.titleColor, kind === 'offline' ? '#ffffff' : '#111827');
  const messageColor = color(cfg.messageColor, kind === 'offline' ? '#e5e7eb' : '#4b5563');
  const buttonBg = color(cfg.buttonBackground, client.accentColor || '#fbbf24');
  const buttonText = color(cfg.buttonTextColor, '#111827');
  const image = embeddedImage ? `<img class="art" src="${embeddedImage}" alt="">` : `<div class="fallback-icon">${kind === 'offline' ? '⌁' : '!'}</div>`;
  const target = JSON.stringify(String(client.url || ''));
  return `<!doctype html>
<html lang="${esc(client.localisation?.language || 'en')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
<title>${title}</title>
<style>
*{box-sizing:border-box}html,body{margin:0;min-height:100%;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:${theme};color:${titleColor}}body{min-height:100vh;display:grid;place-items:center;padding:max(24px,env(safe-area-inset-top)) 24px max(24px,env(safe-area-inset-bottom))}.card{width:min(460px,100%);text-align:center}.art{display:block;width:min(280px,78vw);height:auto;max-height:280px;object-fit:contain;margin:0 auto 24px}.fallback-icon{width:92px;height:92px;border-radius:28px;margin:0 auto 24px;display:grid;place-items:center;background:${buttonBg};color:${buttonText};font-size:44px;font-weight:900}.brand{font-size:11px;letter-spacing:.16em;text-transform:uppercase;opacity:.55;margin-bottom:11px}h1{font-size:${cfg.titleSize}px;font-weight:${cfg.titleWeight};line-height:1.14;margin:0 0 12px;color:${titleColor}}p{font-size:${cfg.messageSize}px;font-weight:${cfg.messageWeight};line-height:1.55;color:${messageColor};margin:0}button{appearance:none;border:0;border-radius:14px;padding:13px 24px;background:${buttonBg};color:${buttonText};font-weight:800;font-size:14px;margin-top:${cfg.buttonMargin}vh;min-width:160px;box-shadow:0 8px 24px rgba(15,23,42,.12)}button:active{transform:translateY(1px)}small{display:block;margin-top:22px;opacity:.42}</style>
</head>
<body>
<div class="card">${image}<div class="brand">${esc(client.appName)}</div><h1>${title}</h1><p>${message}</p><button id="retry">${esc(cfg.buttonText)}</button><small>Powered by Gaotus AppForge</small></div>
<script>document.getElementById('retry').addEventListener('click',function(){var target=${target};if(target){location.replace(target);}else{location.reload();}});</script>
</body>
</html>`;
}

const offlineCfg = {
  background: color(ui.offline_background, client.themeColor || '#111827'),
  title: ui.offline_title || 'No internet connection',
  message: ui.offline_message || 'Please check your connection and try again.',
  titleSize: clamp(ui.offline_title_size, 12, 64, 32),
  messageSize: clamp(ui.offline_message_size, 10, 32, 14),
  titleWeight: weight(ui.offline_title_weight, 700),
  messageWeight: weight(ui.offline_message_weight, 400),
  titleColor: color(ui.offline_title_color, '#ffffff'),
  messageColor: color(ui.offline_message_color, '#e5e7eb'),
  buttonText: ui.offline_button_text || 'Try Again',
  buttonBackground: color(ui.offline_button_background, client.accentColor || '#fbbf24'),
  buttonTextColor: color(ui.offline_button_text_color, '#111827'),
  buttonMargin: clamp(ui.offline_button_margin, 0, 50, 14),
};
const errorCfg = {
  background: color(ui.error_background, '#ffffff'),
  title: ui.error_title || 'Something went wrong',
  message: ui.error_message || "This page couldn't be loaded.",
  titleSize: clamp(ui.error_title_size, 12, 64, 32),
  messageSize: clamp(ui.error_message_size, 10, 32, 14),
  titleWeight: weight(ui.error_title_weight, 600),
  messageWeight: weight(ui.error_message_weight, 400),
  titleColor: color(ui.error_title_color, '#111827'),
  messageColor: color(ui.error_message_color, '#4b5563'),
  buttonText: ui.error_button_text || 'Try Again',
  buttonBackground: color(ui.error_button_background, '#111827'),
  buttonTextColor: color(ui.error_button_text_color, '#ffffff'),
  buttonMargin: clamp(ui.error_button_margin, 0, 50, 25),
};

const [offlineImage, errorImage] = await Promise.all([
  ui.offline_enabled === false ? Promise.resolve('') : imageData(ui.offline_image_url),
  ui.error_enabled === false ? Promise.resolve('') : imageData(ui.error_image_url),
]);
if (ui.offline_enabled !== false && String(ui.offline_image_url || '').trim() && !offlineImage) throw new Error('No Internet Screen image could not be downloaded as a safe HTTPS image');
if (ui.error_enabled !== false && String(ui.error_image_url || '').trim() && !errorImage) throw new Error('Error Screen image could not be downloaded as a safe HTTPS image');

fs.writeFileSync(path.join(rootDir, 'www', 'offline.html'), screenHtml('offline', offlineCfg, offlineImage) + '\n');
fs.writeFileSync(path.join(rootDir, 'www', 'error.html'), screenHtml('error', errorCfg, errorImage) + '\n');
console.log('[AppForge] branded offline + error screens generated', JSON.stringify({ offlineImage: Boolean(offlineImage), errorImage: Boolean(errorImage) }));
