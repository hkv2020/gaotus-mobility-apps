import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';
import { rootDir, readJSON } from './lib.mjs';

const config = readJSON(path.join(rootDir, 'generated-client.json'));
const iconUrl = String(config.iconUrl || '').trim();
const splashUrl = String(config.splashUrl || '').trim();
if (!iconUrl) {
  console.log('[AppForge] no custom icon configured; keeping master assets');
  process.exit(0);
}

function assertHttps(raw, label) {
  const u = new URL(raw);
  if (u.protocol !== 'https:') throw new Error(`${label} must use HTTPS`);
  return u;
}
async function download(raw, label) {
  const u = assertHttps(raw, label);
  const r = await fetch(u, { redirect: 'follow' });
  if (!r.ok) throw new Error(`${label} download failed: HTTP ${r.status}`);
  const type = String(r.headers.get('content-type') || '').toLowerCase();
  if (type && !type.startsWith('image/')) throw new Error(`${label} is not an image (${type})`);
  const buf = Buffer.from(await r.arrayBuffer());
  if (!buf.length || buf.length > 25 * 1024 * 1024) throw new Error(`${label} size is invalid`);
  return buf;
}

const assets = path.join(rootDir, 'assets');
fs.rmSync(assets, { recursive: true, force: true });
fs.mkdirSync(assets, { recursive: true });
const theme = /^#[0-9a-fA-F]{6}$/.test(config.themeColor || '') ? config.themeColor : '#111827';
const icon = await download(iconUrl, 'icon');
const splash = splashUrl ? await download(splashUrl, 'splash') : icon;

await sharp(icon).resize(1024, 1024, { fit: 'contain', background: theme }).png().toFile(path.join(assets, 'icon-only.png'));
await sharp(icon).resize(1024, 1024, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toFile(path.join(assets, 'icon-foreground.png'));
await sharp({ create: { width: 1024, height: 1024, channels: 4, background: theme } }).png().toFile(path.join(assets, 'icon-background.png'));
await sharp(splash).resize(2732, 2732, { fit: 'contain', background: theme }).png().toFile(path.join(assets, 'splash.png'));
await sharp(splash).resize(2732, 2732, { fit: 'contain', background: theme }).png().toFile(path.join(assets, 'splash-dark.png'));
console.log('[AppForge] custom Android branding assets prepared');
