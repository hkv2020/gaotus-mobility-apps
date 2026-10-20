import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

const clientPath = path.join(rootDir, 'generated-client.json');
if (!fs.existsSync(clientPath)) throw new Error('generated-client.json missing. Run npm run generate first.');
const client = validateClient(readJSON(clientPath));

const javaRoot = path.join(rootDir, 'android', 'app', 'src', 'main', 'java');
if (!fs.existsSync(javaRoot)) {
  console.log('[AppForge] Android platform not present, origin policy skipped');
  process.exit(0);
}

function walk(dir, out = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, out);
    else if (ent.name === 'GaotusNativeBridge.java') out.push(full);
  }
  return out;
}

const bridges = walk(javaRoot);
if (bridges.length !== 1) throw new Error(`Expected exactly one GaotusNativeBridge.java, found ${bridges.length}`);
const bridgePath = bridges[0];
let source = fs.readFileSync(bridgePath, 'utf8');

const start = source.indexOf('  private boolean allowed() {');
const end = source.indexOf('\n  private String status(', start);
if (start < 0 || end < 0) throw new Error('Unable to locate generated allowed() policy');

const policy = `  private boolean allowed() {
    // Local AppForge shells are trusted packaged content. Their concrete WebView URL
    // differs across Android System WebView/Capacitor versions, so do not infer
    // trust from a runtime URL that may be about:blank/file/appassets/localhost.
    // Remote client apps remain locked to their configured HTTPS origin below.
    if (localMode) return true;
    try {
      String current = currentUrl();
      if (current.isEmpty()) return false;
      Uri uri = Uri.parse(current);
      String host = uri.getHost();
      String scheme = uri.getScheme();
      if (!same(scheme, allowedScheme) || host == null) return false;
      return same(host, allowedHost) || host.toLowerCase().endsWith("." + allowedHost.toLowerCase());
    } catch (Exception e) {
      return false;
    }
  }
`;

source = source.slice(0, start) + policy + source.slice(end);
source = source.replace(
  '      if (!ok) o.put("error", "origin_not_allowed");',
  '      if (!ok) { o.put("error", "origin_not_allowed"); o.put("currentUrl", currentUrl()); o.put("localMode", localMode); o.put("allowedHost", allowedHost); o.put("allowedScheme", allowedScheme); }'
);

fs.writeFileSync(bridgePath, source);
console.log(`[AppForge] Origin policy applied (${client.mode})`);
