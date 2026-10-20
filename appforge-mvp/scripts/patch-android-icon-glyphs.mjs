import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON } from './lib.mjs';

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, out);
    else if (/MainActivity\.java$/.test(full)) out.push(full);
  }
  return out;
}

const oldGlyph = (key) => ({home:'⌂',search:'⌕',user:'●',account:'●',cart:'▣',phone:'☎',info:'ⓘ',settings:'⚙',link:'↗',menu:'☰',heart:'♥',bell:'●',mail:'✉',chat:'✦',more:'⋯'}[String(key || '').toLowerCase()] || '•');
const betterGlyph = (key) => ({home:'⌂',search:'⌕',user:'👤',account:'👤',cart:'🛒',phone:'☎',info:'ⓘ',settings:'⚙',link:'↗',menu:'☰',heart:'♥',bell:'🔔',mail:'✉',chat:'💬',more:'⋯'}[String(key || '').toLowerCase()] || '•');

const files = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
if (files.length !== 1) throw new Error(`Expected one MainActivity.java, found ${files.length}`);
const file = files[0];
let src = fs.readFileSync(file, 'utf8');
const client = readJSON(path.join(rootDir, 'generated-client.json'));
const ui = client.uiNavigation || {};

function replaceItems(items, methodPrefix) {
  for (const item of Array.isArray(items) ? items : []) {
    const label = JSON.stringify(String(item?.label || ''));
    const target = JSON.stringify(String(item?.url || '/'));
    const before = JSON.stringify(oldGlyph(item?.icon || 'link'));
    const after = JSON.stringify(betterGlyph(item?.icon || 'link'));
    const needle = `${methodPrefix}${label}, ${target}, ${before}`;
    const replacement = `${methodPrefix}${label}, ${target}, ${after}`;
    src = src.replace(needle, replacement);
  }
}

replaceItems(ui.bottom_nav_items, 'addAppForgeBottomItem(bottom, ');
replaceItems(ui.sidebar_items, 'addAppForgeSidebarItem(panel, ');
fs.writeFileSync(file, src);
console.log('[AppForge] navigation icon glyph fidelity patch applied');
