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
const ensureImport = (src, value) => src.includes(`import ${value};`) ? src : src.replace(/(package\s+[\w.]+;\n)/, `$1\nimport ${value};`);

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const links = client.linkHandling || {};
const overrides = client.overrides || {};
const appSettings = client.appSettings || {};
const communication = client.communication || {};
const localisation = client.localisation || {};
const ui = client.uiNavigation || {};
const pdf = client.pdfViewer || {};
const environment = Array.isArray(client.environment) ? client.environment : [];
const files = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
if (files.length !== 1) throw new Error(`Expected one MainActivity.java, found ${files.length}`);
const file = files[0];
let src = fs.readFileSync(file, 'utf8');

const externalMode = links.external_mode === 'in_app' ? 'in_app' : 'external';
const allowSubdomains = links.allow_subdomains !== false;
const externalCommunication = communication.external_phone_email !== false;
const lifecycleUi = appSettings.page_loader === true || appSettings.pull_to_refresh === true;
const offlineEnabled = ui.offline_enabled !== false;
const errorEnabled = ui.error_enabled !== false;
const pdfEnabled = pdf.enabled === true;
const pdfMode = pdf.mode === 'external' ? 'external' : 'in_app';
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

for (const imp of [
  'android.content.Intent', 'android.graphics.Bitmap', 'android.net.Uri', 'android.webkit.WebResourceError',
  'android.webkit.WebResourceRequest', 'android.webkit.WebResourceResponse', 'android.webkit.WebView',
  'com.getcapacitor.Bridge', 'com.getcapacitor.BridgeWebViewClient'
]) src = ensureImport(src, imp);

const method = `
  private boolean appForgeInternalHost(String host) {
    if (host == null || APPFORGE_START_HOST == null || APPFORGE_START_HOST.isEmpty()) return false;
    if (host.equalsIgnoreCase(APPFORGE_START_HOST)) return true;
    return ${allowSubdomains ? 'host.toLowerCase().endsWith("." + APPFORGE_START_HOST.toLowerCase())' : 'false'};
  }

  private boolean appForgeAssetPage(String url) {
    return url != null && url.startsWith("file:///android_asset/public/");
  }

  private boolean openAppForgeExternalIntent(Uri uri) {
    if (uri == null) return false;
    try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); return true; }
    catch (Exception ignored) { return true; }
  }

  private boolean appForgePdf(Uri uri) {
    if (uri == null) return false;
    String path = uri.getPath(); return path != null && path.toLowerCase().endsWith(".pdf");
  }

  private void openAppForgeErrorPage(WebView view, boolean offline) {
    if (view == null) return;
    String target = offline ? "file:///android_asset/public/offline.html" : "file:///android_asset/public/error.html";
    String current = view.getUrl();
    if (appForgeAssetPage(current)) return;
    view.post(() -> view.loadUrl(target));
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
        ${lifecycleUi ? 'if (!appForgeAssetPage(url)) setAppForgeLoading(true);' : ''}
      }

      @Override
      public void onPageFinished(WebView view, String url) {
        super.onPageFinished(view, url);
        injectAppForgeOverrides(view, url);
        ${lifecycleUi ? 'setAppForgeLoading(false);' : ''}
      }

      @Override
      public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
        super.onReceivedError(view, request, error);
        if (request != null && request.isForMainFrame()) {
          ${offlineEnabled ? 'openAppForgeErrorPage(view, true);' : errorEnabled ? 'openAppForgeErrorPage(view, false);' : ''}
          ${lifecycleUi ? 'setAppForgeLoading(false);' : ''}
        }
      }

      @Override
      public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse errorResponse) {
        super.onReceivedHttpError(view, request, errorResponse);
        if (request != null && request.isForMainFrame() && errorResponse != null && errorResponse.getStatusCode() >= 400) {
          ${errorEnabled ? 'openAppForgeErrorPage(view, false);' : ''}
          ${lifecycleUi ? 'setAppForgeLoading(false);' : ''}
        }
      }

      @Override
      public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        Uri uri = request.getUrl();
        String scheme = uri != null ? uri.getScheme() : null;
        String host = uri != null ? uri.getHost() : null;
        ${externalCommunication ? `if (scheme != null && (scheme.equalsIgnoreCase("tel") || scheme.equalsIgnoreCase("mailto") || scheme.equalsIgnoreCase("sms") || scheme.equalsIgnoreCase("smsto") || scheme.equalsIgnoreCase("geo") || scheme.equalsIgnoreCase("market") || scheme.equalsIgnoreCase("whatsapp"))) return openAppForgeExternalIntent(uri);` : ''}
        ${pdfEnabled ? `if (appForgePdf(uri)) {
          if (${JSON.stringify(pdfMode)}.equals("external")) return openAppForgeExternalIntent(uri);
          String viewer = "https://docs.google.com/gview?embedded=1&url=" + Uri.encode(uri.toString()); view.loadUrl(viewer); return true;
        }
        if (host != null && (host.equalsIgnoreCase("docs.google.com") || host.toLowerCase().endsWith(".googleusercontent.com"))) return false;` : ''}
        boolean web = "http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme);
        if (web && !appForgeInternalHost(host)) {
          if (${JSON.stringify(externalMode)}.equals("in_app")) { view.loadUrl(uri.toString()); return true; }
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
if (src.includes('      applyAppForgeRuntime(webView);\n')) src = src.replace('      applyAppForgeRuntime(webView);\n', '      applyAppForgeRuntime(webView);\n      installAppForgeWebViewClient(webView);\n');
else throw new Error('AppForge runtime call not found for WebView client install');
fs.writeFileSync(file, src);
console.log(`[AppForge] WebView runtime externalMode=${externalMode}, env=${Object.keys(envObject).length}, offline=${offlineEnabled}, error=${errorEnabled}, pdf=${pdfEnabled}:${pdfMode}`);
