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

const source = `package ${pkg};

import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebView;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
  private OnBackPressedCallback appForgeBackCallback;
  private static final boolean APPFORGE_REMOTE_MODE = ${remote ? 'true' : 'false'};
  private static final String APPFORGE_START_URL = ${JSON.stringify(startUrl)};
  private static final String APPFORGE_START_HOST = ${JSON.stringify(startHost)};

  private boolean sameHost(String a, String b) {
    return a != null && b != null && a.equalsIgnoreCase(b);
  }

  private void enforceConfiguredSite(WebView webView) {
    if (!APPFORGE_REMOTE_MODE || webView == null || APPFORGE_START_URL.isEmpty()) return;

    webView.post(() -> {
      try {
        String current = webView.getUrl();
        String currentHost = null;
        if (current != null && !current.isEmpty()) currentHost = Uri.parse(current).getHost();

        // If Android restored an old WebView task/history for the same package ID,
        // move only that stale navigation state to the newly configured AppForge site.
        if (!sameHost(currentHost, APPFORGE_START_HOST)) {
          webView.stopLoading();
          webView.clearHistory();
          webView.loadUrl(APPFORGE_START_URL);
          webView.postDelayed(webView::clearHistory, 750);
        }
      } catch (Exception ignored) {
        webView.loadUrl(APPFORGE_START_URL);
      }
    });
  }

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    WebView webView = getBridge() != null ? getBridge().getWebView() : null;
    if (webView != null) {
      webView.addJavascriptInterface(new GaotusNativeBridge(this), "GaotusNativeAndroid");
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

        setEnabled(false);
        getOnBackPressedDispatcher().onBackPressed();
      }
    };

    getOnBackPressedDispatcher().addCallback(this, appForgeBackCallback);
  }
}
`;

fs.writeFileSync(file, source);
console.log(`[AppForge] Android Back + configured-site guard active${remote ? ` -> ${startUrl}` : ''}`);
