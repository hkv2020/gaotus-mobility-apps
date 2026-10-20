import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const ui = client.uiNavigation || {};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
const theme = /^#[0-9a-fA-F]{6}$/.test(String(client.themeColor || '')) ? client.themeColor : '#111827';
const accent = /^#[0-9a-fA-F]{6}$/.test(String(client.accentColor || '')) ? client.accentColor : '#fbbf24';
const title = esc(ui.offline_title || 'No internet connection');
const message = esc(ui.offline_message || 'Please check your connection and try again.');
const app = esc(client.appName);

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>${title}</title>
<style>
*{box-sizing:border-box}html,body{margin:0;min-height:100%;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:${theme};color:#fff}body{min-height:100vh;display:grid;place-items:center;padding:28px}.card{width:min(440px,100%);text-align:center}.icon{width:86px;height:86px;border-radius:24px;margin:0 auto 24px;display:grid;place-items:center;background:${accent};color:${theme};font-size:38px;font-weight:900}.brand{font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.68;margin-bottom:10px}h1{font-size:28px;line-height:1.15;margin:0 0 12px}p{font-size:15px;line-height:1.6;opacity:.78;margin:0 0 24px}button{appearance:none;border:0;border-radius:12px;padding:13px 22px;background:${accent};color:${theme};font-weight:800;font-size:14px}small{display:block;margin-top:24px;opacity:.45}</style>
</head>
<body>
<div class="card"><div class="icon">↻</div><div class="brand">${app}</div><h1>${title}</h1><p>${message}</p><button onclick="location.reload()">Try again</button><small>Powered by Gaotus AppForge</small></div>
</body>
</html>`;
fs.writeFileSync(path.join(rootDir, 'www', 'offline.html'), html + '\n');
console.log('[AppForge] branded offline/error screen generated');
