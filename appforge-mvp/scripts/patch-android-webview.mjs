import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, out);
    else if (/MainActivity\.java$/.test(full)) out.push(full);
  }
  return out;
}

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const links = client.linkHandling || {};
const overrides = client.overrides || {};
const appSettings = client.appSettings || {};
const communication = client.communication || {};
const localisation = client.localisation || {};
const environment = Array.isArray(client.environment) ? client.environment : [];
const files = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
if (files.length !== 1) throw new Error(`Expected one MainActivity.java, found ${files.length}`);
const file = files[0];
let src = fs.readFileSync(file, 'utf8');

const externalMode = links.external_mode === 'in_app' ? 'in_app' : 'external';
const allowSubdomains = links.allow_subdomains !== false;
const externalCommunication = communication.external_phone_email !== false;
const lifecycleUi = appSettings.page_loader === true || appSettings.pull_to_refresh === true;
const css64 = Buffer.from(String(overrides.custom_css || ''), 'utf8').toString('base64');
const js64 = Buffer.from(String(overrides.custom_js || ''), 'utf8').toString('base64');
const envObject = {};
for (const row of environment) {
  if (!row || typeof row !== 'object') continue;
  const key = String(row.key || '').replace(/[^A-Za-z0-9_]/g, '').toUpperCase();
  if (key) envObject[key] = String(row.value ?? '');
}
const env64 = Buffer.from(JSON.stringify(envObject), 'utf8').toString('base64');
const lang = String(localisation.language || 'en').replace(/[^A-Za-z_-]/g, '') || 'en';
const rtl = localisation.rtl === true;

if (!src.includes('import android.content.Intent;')) src = src.replace('import android.app.AlertDialog;\n', 'import android.app.AlertDialog;\nimport android.content.Intent;\n');
if (!src.includes('import android.graphics.Bitmap;')) src = src.replace('import android.graphics.Color;\n', 'import android.graphics.Color;\nimport android.graphics.Bitmap;\n');
if (!src.includes('import android.webkit.WebResourceRequest;')) src = src.replace('import android.webkit.WebSettings;\n', 'import android.webkit.WebSettings;\nimport android.webkit.WebResourceRequest;\n');
if (!src.includes('import com.getcapacitor.Bridge;')) src = src.replace('import com.getcapacitor.BridgeActivity;\n', 'import com.getcapacitor.BridgeActivity;\nimport com.getcapacitor.Bridge;\nimport com.getcapacitor.BridgeWebViewClient;\n');

const method = `
  private boolean appForgeInternalHost(String host) {
    if (host == null || APPFORGE_START_HOST == null || APPFORGE_START_HOST.isEmpty()) return false;
    if (host.equalsIgnoreCase(APPFORGE_START_HOST)) return true;
    return ${allowSubdomains ? 'host.toLowerCase().endsWith("." + APPFORGE_START_HOST.toLowerCase())' : 'false'};
  }

  private boolean openAppForgeExternalIntent(Uri uri) {
    if (uri == null) return false;
    try {
      startActivity(new Intent(Intent.ACTION_VIEW, uri));
      return true;
    } catch (Exception ignored) { return true; }
  }

  private void injectAppForgeOverrides(WebView view, String url) {
    try {
      String host = Uri.parse(url == null ? "" : url).getHost();
      if (!appForgeInternalHost(host)) return;
      String script = "(function(){try{" +
        "var e=JSON.parse(atob('${env64}'));window.GaotusEnv=Object.freeze(e);" +
        "document.documentElement.lang='${lang}';document.documentElement.dir='${rtl ? 'rtl' : 'ltr'}';" +
        "var c=atob('${css64}');if(c){var s=document.getElementById('gaotus-appforge-css');if(!s){s=document.createElement('style');s.id='gaotus-appforge-css';document.head.appendChild(s);}s.textContent=c;}" +
        "var j=atob('${js64}');if(j){(0,eval)(j);}" +
        "}catch(e){console.warn('AppForge override',e);}})();";
      view.evaluateJavascript(script, null);
    } catch (Exception ignored) {}
  }

  private void installAppForgeWebViewClient(WebView webView) {
    if (webView == null || getBridge() == null) return;
    Bridge bridge = getBridge();
    webView.setWebViewClient(new BridgeWebViewClient(bridge) {
      @Override
      public void onPageStarted(WebView view, String url, Bitmap favicon) {
        super.onPageStarted(view, url, favicon);
        ${lifecycleUi ? 'setAppForgeLoading(true);' : ''}
      }

      @Override
      public void onPageFinished(WebView view, String url) {
        super.onPageFinished(view, url);
        injectAppForgeOverrides(view, url);
        ${lifecycleUi ? 'setAppForgeLoading(false);' : ''}
      }

      @Override
      public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        Uri uri = request.getUrl();
        String scheme = uri != null ? uri.getScheme() : null;
        String host = uri != null ? uri.getHost() : null;
        ${externalCommunication ? `if (scheme != null && (scheme.equalsIgnoreCase("tel") || scheme.equalsIgnoreCase("mailto") || scheme.equalsIgnoreCase("sms") || scheme.equalsIgnoreCase("smsto") || scheme.equalsIgnoreCase("geo") || scheme.equalsIgnoreCase("market") || scheme.equalsIgnoreCase("whatsapp"))) {
          return openAppForgeExternalIntent(uri);
        }` : ''}
        boolean web = "http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme);
        if (web && !appForgeInternalHost(host)) {
          if (${JSON.stringify(externalMode)}.equals("in_app")) {
            view.loadUrl(uri.toString());
            return true;
          }
          return openAppForgeExternalIntent(uri);
        }
        return super.shouldOverrideUrlLoading(view, request);
      }
    });
  }
`;

const marker = '  @Override\n  protected void onCreate(Bundle savedInstanceState) {';
if (!src.includes(marker)) throw new Error('MainActivity onCreate marker not found for webview patch');
src = src.replace(marker, method + '\n' + marker);
if (src.includes('      applyAppForgeRuntime(webView);\n')) {
  src = src.replace('      applyAppForgeRuntime(webView);\n', '      applyAppForgeRuntime(webView);\n      installAppForgeWebViewClient(webView);\n');
} else {
  throw new Error('AppForge runtime call not found for WebView client install');
}
fs.writeFileSync(file, src);
console.log(`[AppForge] WebView runtime: externalMode=${externalMode}, communication=${externalCommunication}, env=${Object.keys(envObject).length}, lang=${lang}, rtl=${rtl}, css=${css64.length > 0}, js=${js64.length > 0}, lifecycleUI=${lifecycleUi}`);
