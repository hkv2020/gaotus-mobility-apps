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
const javaArray = (values) => `new String[]{${(Array.isArray(values) ? values : []).map((v) => JSON.stringify(String(v))).join(',')}}`;

const clientPath = path.join(rootDir, 'generated-client.json');
if (!fs.existsSync(clientPath)) throw new Error('generated-client.json missing');
const client = validateClient(readJSON(clientPath));
const files = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
if (files.length !== 1) throw new Error(`Expected one MainActivity.java, found ${files.length}`);
const file = files[0];
const original = fs.readFileSync(file, 'utf8');
const pkg = (original.match(/package\s+([\w.]+)\s*;/) || [])[1];
if (!pkg) throw new Error('Could not determine Android package from MainActivity.java');

const remote = client.mode === 'remote';
const startUrl = remote ? String(client.url) : '';
const startHost = remote ? new URL(client.url).hostname : '';
const settings = client.appSettings || {};
const links = client.linkHandling || {};
const overrides = client.overrides || {};
const back = client.backExit || {};
const bool = (v, d = false) => typeof v === 'boolean' ? v : d;
const color = (v, fallback) => /^#[0-9a-fA-F]{6}$/.test(String(v || '')) ? String(v) : fallback;
const orientation = ['portrait', 'landscape', 'both'].includes(settings.orientation) ? settings.orientation : 'portrait';
const exitMode = back.mode === 'immediate' ? 'immediate' : (settings.confirm_exit === false ? 'immediate' : 'confirm');
const exitMessage = String(back.message || 'Press back again to exit').slice(0, 100);
const exitPages = Array.isArray(back.exit_pages) ? back.exit_pages.slice(0, 30) : [];
const disabledPages = Array.isArray(back.disable_back_pages) ? back.disable_back_pages.slice(0, 30) : [];
const headers = {};
for (const line of String(overrides.custom_headers || '').split(/\r?\n/)) {
  const idx = line.indexOf(':');
  if (idx > 0) {
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim();
    if (key && value) headers[key] = value;
  }
}

const source = `package ${pkg};

import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Toast;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;
import java.util.HashMap;
import java.util.Map;

public class MainActivity extends BridgeActivity {
  private OnBackPressedCallback appForgeBackCallback;
  private long appForgeLastBackAt = 0L;
  private static final boolean APPFORGE_REMOTE_MODE = ${remote ? 'true' : 'false'};
  private static final String APPFORGE_START_URL = ${JSON.stringify(startUrl)};
  private static final String APPFORGE_START_HOST = ${JSON.stringify(startHost)};
  private static final String APPFORGE_ORIENTATION = ${JSON.stringify(orientation)};
  private static final boolean APPFORGE_FULLSCREEN = ${bool(settings.fullscreen) ? 'true' : 'false'};
  private static final boolean APPFORGE_PINCH_ZOOM = ${bool(settings.pinch_zoom) ? 'true' : 'false'};
  private static final boolean APPFORGE_DISABLE_CACHE = ${bool(settings.disable_cache) ? 'true' : 'false'};
  private static final boolean APPFORGE_KIOSK = ${bool(settings.kiosk_mode) ? 'true' : 'false'};
  private static final boolean APPFORGE_DISABLE_OVERSCROLL = ${bool(settings.scroll_bounce) ? 'true' : 'false'};
  private static final String APPFORGE_STATUS_BAR = ${JSON.stringify(color(settings.status_bar_color, '#111827'))};
  private static final String APPFORGE_NAV_BAR = ${JSON.stringify(color(settings.navigation_bar_color, '#111827'))};
  private static final String APPFORGE_USER_AGENT = ${JSON.stringify(String(overrides.user_agent || ''))};
  private static final boolean APPFORGE_COOKIE_PERSISTENCE = ${bool(overrides.cookie_persistence, true) ? 'true' : 'false'};
  private static final boolean APPFORGE_DISABLE_BACK = ${bool(back.disable_back_button) ? 'true' : 'false'};
  private static final String APPFORGE_EXIT_MODE = ${JSON.stringify(exitMode)};
  private static final String APPFORGE_EXIT_MESSAGE = ${JSON.stringify(exitMessage)};
  private static final String[] APPFORGE_EXIT_PAGES = ${javaArray(exitPages)};
  private static final String[] APPFORGE_DISABLE_BACK_PAGES = ${javaArray(disabledPages)};

  private boolean sameHost(String a, String b) {
    return a != null && b != null && a.equalsIgnoreCase(b);
  }

  private Map<String,String> appForgeHeaders() {
    Map<String,String> values = new HashMap<>();
${Object.entries(headers).map(([k,v]) => `    values.put(${JSON.stringify(k)}, ${JSON.stringify(v)});`).join('\n')}
    return values;
  }

  private void applyAppForgeRuntime(WebView webView) {
    try {
      if ("landscape".equals(APPFORGE_ORIENTATION)) setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
      else if ("both".equals(APPFORGE_ORIENTATION)) setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
      else setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
      getWindow().setStatusBarColor(Color.parseColor(APPFORGE_STATUS_BAR));
      getWindow().setNavigationBarColor(Color.parseColor(APPFORGE_NAV_BAR));
      if (APPFORGE_FULLSCREEN) getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
      if (webView == null) return;
      WebSettings ws = webView.getSettings();
      ws.setBuiltInZoomControls(APPFORGE_PINCH_ZOOM);
      ws.setDisplayZoomControls(false);
      ws.setSupportZoom(APPFORGE_PINCH_ZOOM);
      ws.setCacheMode(APPFORGE_DISABLE_CACHE ? WebSettings.LOAD_NO_CACHE : WebSettings.LOAD_DEFAULT);
      if (!APPFORGE_USER_AGENT.isEmpty()) ws.setUserAgentString(APPFORGE_USER_AGENT);
      if (APPFORGE_DISABLE_OVERSCROLL) webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
      if (!APPFORGE_COOKIE_PERSISTENCE) CookieManager.getInstance().removeAllCookies(null);
    } catch (Exception ignored) {}
  }

  private void enforceConfiguredSite(WebView webView) {
    if (!APPFORGE_REMOTE_MODE || webView == null || APPFORGE_START_URL.isEmpty()) return;
    webView.post(() -> {
      try {
        String current = webView.getUrl();
        String currentHost = current != null && !current.isEmpty() ? Uri.parse(current).getHost() : null;
        if (!sameHost(currentHost, APPFORGE_START_HOST)) {
          webView.stopLoading();
          webView.clearHistory();
          Map<String,String> headers = appForgeHeaders();
          if (headers.isEmpty()) webView.loadUrl(APPFORGE_START_URL); else webView.loadUrl(APPFORGE_START_URL, headers);
          webView.postDelayed(webView::clearHistory, 750);
        }
      } catch (Exception ignored) { webView.loadUrl(APPFORGE_START_URL); }
    });
  }

  private String appForgePath(String value) {
    if (value == null || value.isEmpty()) return "/";
    try {
      Uri uri = Uri.parse(value);
      String path = uri.getPath();
      if (path == null || path.isEmpty()) path = value.startsWith("/") ? value : "/" + value;
      if (path.length() > 1 && path.endsWith("/")) path = path.substring(0, path.length() - 1);
      return path;
    } catch (Exception ignored) { return value; }
  }

  private boolean matchesAppForgePage(String current, String[] configured) {
    if (configured == null || configured.length == 0 || current == null) return false;
    String currentPath = appForgePath(current);
    for (String target : configured) {
      if (target == null || target.isEmpty()) continue;
      if (currentPath.equalsIgnoreCase(appForgePath(target))) return true;
    }
    return false;
  }

  private boolean atAppForgeRoot(String current) {
    if (!APPFORGE_REMOTE_MODE || current == null || current.isEmpty()) return false;
    try {
      Uri cur = Uri.parse(current); Uri start = Uri.parse(APPFORGE_START_URL);
      return sameHost(cur.getHost(), start.getHost()) && appForgePath(cur.getPath()).equalsIgnoreCase(appForgePath(start.getPath()));
    } catch (Exception ignored) { return false; }
  }

  private void finishAppForge() {
    appForgeBackCallback.setEnabled(false);
    getOnBackPressedDispatcher().onBackPressed();
  }

  private void exitAppForge() {
    if (APPFORGE_KIOSK) return;
    if ("immediate".equals(APPFORGE_EXIT_MODE)) { finishAppForge(); return; }
    long now = System.currentTimeMillis();
    if (now - appForgeLastBackAt <= 2000L) { finishAppForge(); return; }
    appForgeLastBackAt = now;
    Toast.makeText(this, APPFORGE_EXIT_MESSAGE, Toast.LENGTH_SHORT).show();
  }

  private boolean shouldBlockAppForgeBack(String current) {
    if (!APPFORGE_DISABLE_BACK) return false;
    if (APPFORGE_DISABLE_BACK_PAGES.length == 0) return true;
    return matchesAppForgePage(current, APPFORGE_DISABLE_BACK_PAGES);
  }

  private boolean shouldExitAppForge(String current, WebView webView) {
    if (APPFORGE_EXIT_PAGES.length > 0) return matchesAppForgePage(current, APPFORGE_EXIT_PAGES);
    if (atAppForgeRoot(current)) return true;
    return webView == null || !webView.canGoBack();
  }

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    WebView webView = getBridge() != null ? getBridge().getWebView() : null;
    if (webView != null) {
      webView.addJavascriptInterface(new GaotusNativeBridge(this), "GaotusNativeAndroid");
      applyAppForgeRuntime(webView);
      enforceConfiguredSite(webView);
    }

    appForgeBackCallback = new OnBackPressedCallback(true) {
      @Override
      public void handleOnBackPressed() {
        WebView currentWebView = getBridge() != null ? getBridge().getWebView() : null;
        String current = currentWebView != null ? currentWebView.getUrl() : "";
        if (shouldBlockAppForgeBack(current)) return;
        if (shouldExitAppForge(current, currentWebView)) { exitAppForge(); return; }
        if (currentWebView != null && currentWebView.canGoBack()) { currentWebView.goBack(); return; }
        if (APPFORGE_EXIT_PAGES.length > 0) return;
        exitAppForge();
      }
    };
    getOnBackPressedDispatcher().addCallback(this, appForgeBackCallback);
  }
}
`;

fs.writeFileSync(file, source);

const manifest = path.join(rootDir, 'android', 'app', 'src', 'main', 'AndroidManifest.xml');
let xml = fs.readFileSync(manifest, 'utf8');
xml = xml.replace(/\s*<!-- appforge-generated-intent-filter -->[\s\S]*?(?=\s*<\/activity>)/g, '');
let intentFilters = '';
if (remote && bool(links.deep_linking, false)) {
  intentFilters += `\n            <intent-filter android:autoVerify="true">\n                <action android:name="android.intent.action.VIEW" />\n                <category android:name="android.intent.category.DEFAULT" />\n                <category android:name="android.intent.category.BROWSABLE" />\n                <data android:scheme="https" android:host="${startHost}" />\n            </intent-filter>`;
}
if (String(links.custom_scheme || '').trim()) {
  const scheme = String(links.custom_scheme).trim().replace(/[^A-Za-z0-9+.-]/g, '');
  if (scheme) intentFilters += `\n            <intent-filter>\n                <action android:name="android.intent.action.VIEW" />\n                <category android:name="android.intent.category.DEFAULT" />\n                <category android:name="android.intent.category.BROWSABLE" />\n                <data android:scheme="${scheme}" />\n            </intent-filter>`;
}
if (intentFilters) xml = xml.replace('</activity>', `\n            <!-- appforge-generated-intent-filter -->${intentFilters}\n        </activity>`);
fs.writeFileSync(manifest, xml);
console.log(`[AppForge] Android runtime + Back/Exit active mode=${exitMode}, disableBack=${Boolean(back.disable_back_button)}, exitPages=${exitPages.length}`);
