import fs from 'node:fs';
import path from 'node:path';
import { rootDir } from './lib.mjs';

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, out);
    else if (/MainActivity\.java$/.test(full)) out.push(full);
  }
  return out;
}

const files = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
if (files.length !== 1) throw new Error(`Expected one MainActivity.java, found ${files.length}`);
const file = files[0];
let src = fs.readFileSync(file, 'utf8');

// Cross-patcher reconciliation: generated sidebar rows must bind to the persistent panel field.
// This is intentionally centralized so future native modules cannot leave stale local identifiers behind.
src = src.replace(/addAppForgeSidebarItem\(panel,/g, 'addAppForgeSidebarItem(appForgeSidebarPanel,');

const unresolved = [];
if (src.includes('addAppForgeSidebarItem(panel,')) unresolved.push('stale sidebar panel identifier');
if (src.includes('APPFORGE_PUSH_INITIALIZED')) {
  for (const statement of [
    'import android.Manifest;',
    'import android.content.pm.PackageManager;',
    'import android.os.Build;',
  ]) if (!src.includes(statement)) unresolved.push(`push import missing: ${statement}`);
}
if (unresolved.length) throw new Error(`Generated Android reconciliation failed: ${unresolved.join('; ')}`);

fs.writeFileSync(file, src);
console.log('[AppForge] generated Android source reconciled across UI/push patchers');
