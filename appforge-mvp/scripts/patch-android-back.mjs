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
const original = fs.readFileSync(file, 'utf8');
const pkg = (original.match(/package\s+([\w.]+)\s*;/) || [])[1];
if (!pkg) throw new Error('Could not determine Android package from MainActivity.java');

const source = `package ${pkg};

import android.os.Bundle;
import android.webkit.WebView;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
  private OnBackPressedCallback appForgeBackCallback;

  @Override
  protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    if (getBridge() != null && getBridge().getWebView() != null) {
      getBridge().getWebView().addJavascriptInterface(new GaotusNativeBridge(this), "GaotusNativeAndroid");
    }

    appForgeBackCallback = new OnBackPressedCallback(true) {
      @Override
      public void handleOnBackPressed() {
        WebView webView = getBridge() != null ? getBridge().getWebView() : null;

        if (webView != null && webView.canGoBack()) {
          webView.goBack();
          return;
        }

        // No browser history left: temporarily disable this callback and
        // let Android perform the normal app-level Back action.
        setEnabled(false);
        getOnBackPressedDispatcher().onBackPressed();
      }
    };

    getOnBackPressedDispatcher().addCallback(this, appForgeBackCallback);
  }
}
`;

fs.writeFileSync(file, source);
console.log('[AppForge] Android Back uses OnBackPressedDispatcher and WebView history');
