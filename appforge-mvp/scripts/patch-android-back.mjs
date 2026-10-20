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
const permissions = client.permissions || {};
const links = client.linkHandling || {};
const overrides = client.overrides || {};

const bool = (v, d = false) => typeof v === 'boolean' ? v : d;
const color = (v, fallback) => /^#[0-9a-fA-F]{6}$/.test(String(v || '')) ? String(v) : fallback;
const orientation = ['portrait', 'landscape', 'both'].includes(settings.orientation) ? settings.orientation : 'portrait';
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

import android.app.AlertDialog;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;
import java.util.HashMap;
import java.util.Map;

public class MainActivity extends BridgeActivity {
  private OnBackPressedCallback appForgeBackCallback;
  private static final boolean APPFORGE_REMOTE_MODE = ${remote ? 'true' : 'false'};
  private static final String APPFORGE_START_URL = ${JSON.stringify(startUrl)};
  private static final String APPFORGE_START_HOST = ${JSON.stringify(startHost)};
  private static final String APPFORGE_ORIENTATION = ${JSON.stringify(orientation)};
  private static final boolean APPFORGE_FULLSCREEN = ${bool(settings.fullscreen) ? 'true' : 'false'};
  private static final boolean APPFORGE_PINCH_ZOOM = ${bool(settings.pinch_zoom) ? 'true' : 'false'};
  private static final boolean APPFORGE_DISABLE_CACHE = ${bool(settings.disable_cache) ? 'true' : 'false'};
  private static final boolean APPFORGE_KIOSK = ${bool(settings.kiosk_mode) ? 'true' : 'false'};
  private static final boolean APPFORGE_DISABLE_OVERSCROLL = ${bool(settings.scroll_bounce) ? 'true' : 'false'};
  private static final boolean APPFORGE_CONFIRM_EXIT = ${bool(settings.confirm_exit, true) ? 'true' : 'false'};
  private static final String APPFORGE_STATUS_BAR = ${JSON.stringify(color(settings.status_bar_color, '#111827'))};
  private static final String APPFORGE_NAV_BAR = ${JSON.stringify(color(settings.navigation_bar_color, '#111827'))};
  private static final String APPFORGE_USER_AGENT = ${JSON.stringify(String(overrides.user_agent || ''))};
  private static final boolean APPFORGE_COOKIE_PERSISTENCE = ${bool(overrides.cookie_persistence, true) ? 'true' : 'false'};

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
      if (APPFORGE_FULLSCREEN) {
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
      }

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
        String currentHost = null;
        if (current != null && !current.isEmpty()) currentHost = Uri.parse(current).getHost();
        if (!sameHost(currentHost, APPFORGE_START_HOST)) {
          webView.stopLoading();
          webView.clearHistory();
          Map<String,String> headers = appForgeHeaders();
          if (headers.isEmpty()) webView.loadUrl(APPFORGE_START_URL);
          else webView.loadUrl(APPFORGE_START_URL, headers);
          webView.postDelayed(webView::clearHistory, 750);
        }
      } catch (Exception ignored) {
        webView.loadUrl(APPFORGE_START_URL);
      }
    });
  }

  private void exitAppForge() {
    if (APPFORGE_KIOSK) return;
    if (!APPFORGE_CONFIRM_EXIT) {
      appForgeBackCallback.setEnabled(false);
      getOnBackPressedDispatcher().onBackPressed();
      return;
    }
    new AlertDialog.Builder(this)
      .setTitle("Exit app?")
      .setMessage("Do you want to close the app?")
      .setNegativeButton("Cancel", null)
      .setPositiveButton("Exit", (dialog, which) -> {
        appForgeBackCallback.setEnabled(false);
        getOnBackPressedDispatcher().onBackPressed();
      }).show();
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
        if (currentWebView != null && currentWebView.canGoBack()) {
          currentWebView.goBack();
          return;
        }
        exitAppForge();
      }
    };
    getOnBackPressedDispatcher().addCallback(this, appForgeBackCallback);
  }
}
`;

fs.writeFileSync(file, source);

// Reconcile manifest permissions with the AppForge permission switches.
const manifest = path.join(rootDir, 'android', 'app', 'src', 'main', 'AndroidManifest.xml');
let xml = fs.readFileSync(manifest, 'utf8');
const permissionNames = [
  'android.permission.CAMERA',
  'android.permission.VIBRATE',
  'android.permission.ACCESS_COARSE_LOCATION',
  'android.permission.ACCESS_FINE_LOCATION',
  'android.permission.RECORD_AUDIO'
];
for (const name of permissionNames) {
  xml = xml.replace(new RegExp(`\\s*<uses-permission android:name=["']${name.replace(/\./g, '\\.') }["']\\s*/>`, 'g'), '');
}
const wanted = [];
if (bool(permissions.camera, true)) wanted.push('android.permission.CAMERA');
if (bool(permissions.vibration, true)) wanted.push('android.permission.VIBRATE');
if (bool(permissions.location, true)) wanted.push('android.permission.ACCESS_COARSE_LOCATION', 'android.permission.ACCESS_FINE_LOCATION');
if (bool(permissions.microphone, false)) wanted.push('android.permission.RECORD_AUDIO');
for (const name of wanted) xml = xml.replace('<application', `    <uses-permission android:name="${name}" />\n\n    <application`);

// Deep link and custom URL scheme intent filters are added to the generated MainActivity.
const activityClose = '</activity>';
let intentFilters = '';
if (remote && bool(links.deep_linking, false)) {
  intentFilters += `\n            <intent-filter android:autoVerify="true">\n                <action android:name="android.intent.action.VIEW" />\n                <category android:name="android.intent.category.DEFAULT" />\n                <category android:name="android.intent.category.BROWSABLE" />\n                <data android:scheme="https" android:host="${startHost}" />\n            </intent-filter>`;
}
if (String(links.custom_scheme || '').trim()) {
  const scheme = String(links.custom_scheme).trim().replace(/[^A-Za-z0-9+.-]/g, '');
  if (scheme) intentFilters += `\n            <intent-filter>\n                <action android:name="android.intent.action.VIEW" />\n                <category android:name="android.intent.category.DEFAULT" />\n                <category android:name="android.intent.category.BROWSABLE" />\n                <data android:scheme="${scheme}" />\n            </intent-filter>`;
}
if (intentFilters && !xml.includes('appforge-generated-intent-filter')) {
  intentFilters = `\n            <!-- appforge-generated-intent-filter -->${intentFilters}\n`;
  xml = xml.replace(activityClose, `${intentFilters}        ${activityClose}`);
}
fs.writeFileSync(manifest, xml);

console.log(`[AppForge] Android runtime settings + Back + configured-site guard active${remote ? ` -> ${startUrl}` : ''}`);
