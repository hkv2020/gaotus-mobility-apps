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
if (!src.includes('APPFORGE_WEBVIEW_BACK')) {
  src = src.replace(/\n}\s*$/, `\n\n  // APPFORGE_WEBVIEW_BACK\n  @Override\n  public void onBackPressed() {\n    if (getBridge() != null && getBridge().getWebView() != null && getBridge().getWebView().canGoBack()) {\n      getBridge().getWebView().goBack();\n      return;\n    }\n    super.onBackPressed();\n  }\n}\n`);
  fs.writeFileSync(file, src);
}
console.log('[AppForge] Android WebView back navigation patched');
