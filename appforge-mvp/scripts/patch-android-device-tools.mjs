import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, out); else out.push(full);
  }
  return out;
}
const ensureImport = (src, value) => src.includes(`import ${value};`) ? src : src.replace(/(package\s+[\w.]+;\n)/, `$1\nimport ${value};`);

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const files = client.fileHandling || {};
const device = client.deviceHardware || {};
const downloads = files.downloads_enabled === true;
const wifiOnly = files.wifi_only === true;
const publicDownloads = files.download_to_public !== false;
const clipboard = device.clipboard_enabled === true;
const appSettings = device.open_app_settings === true;

const javaFiles = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
const mains = javaFiles.filter((f) => /MainActivity\.java$/.test(f));
const bridges = javaFiles.filter((f) => /GaotusNativeBridge\.java$/.test(f));
if (mains.length !== 1) throw new Error(`Expected one MainActivity.java, found ${mains.length}`);
if (bridges.length !== 1) throw new Error(`Expected one GaotusNativeBridge.java, found ${bridges.length}`);

let main = fs.readFileSync(mains[0], 'utf8');
let bridge = fs.readFileSync(bridges[0], 'utf8');

// Trusted-origin web SDK is always injected. Native bridge methods still enforce origin policy.
const sdkMethod = `
  private void injectAppForgeNativeSdk(WebView view, String url) {
    try {
      String host = Uri.parse(url == null ? "" : url).getHost();
      if (!appForgeInternalHost(host)) return;
      String js = "(function(){try{" +
        "var a=window.GaotusNativeAndroid;if(!a)return;" +
        "var p=function(v){try{return JSON.parse(v)}catch(e){return {ok:false,error:'invalid_native_response'}}};" +
        "var n={" +
        "ping:function(){return p(a.ping())}," +
        "deviceInfo:function(){return p(a.deviceInfo())}," +
        "share:function(v){return p(a.share(JSON.stringify(v||{})))}," +
        "haptic:function(v){return p(a.haptic(v||'medium'))}," +
        "openExternal:function(v){return p(a.openExternal(String(v||'')))}," +
        "openCamera:function(){return p(a.openCamera())}," +
        "toast:function(v){return p(a.toast(String(v||''))) }" +
        ${clipboard ? `",copyToClipboard:function(v){return p(a.copyToClipboard(String(v||'')))}" +` : ''}
        ${appSettings ? `",openAppSettings:function(){return p(a.openAppSettings())}" +` : ''}
        "};window.GaotusNative=Object.freeze(n);" +
        "}catch(e){console.warn('AppForge native SDK',e);}})();";
      view.evaluateJavascript(js, null);
    } catch (Exception ignored) {}
  }
`;

if (!main.includes('injectAppForgeNativeSdk(WebView view, String url)')) {
  const marker = '  private void installAppForgeWebViewClient(WebView webView) {';
  if (!main.includes(marker)) throw new Error('AppForge WebView client marker missing for trusted SDK injection');
  main = main.replace(marker, sdkMethod + '\n' + marker);
}
if (!main.includes('injectAppForgeNativeSdk(view, url);')) {
  const marker = '        injectAppForgeOverrides(view, url);';
  if (!main.includes(marker)) throw new Error('onPageFinished override marker missing for trusted SDK injection');
  main = main.replace(marker, '        injectAppForgeNativeSdk(view, url);\n' + marker);
}

if (downloads) {
  for (const imp of [
    'android.Manifest','android.app.DownloadManager','android.content.Context','android.content.pm.PackageManager',
    'android.os.Build','android.os.Environment','android.webkit.CookieManager','android.webkit.URLUtil','android.widget.Toast'
  ]) main = ensureImport(main, imp);

  const downloadMethod = `
  private void installAppForgeDownloads(WebView webView) {
    if (webView == null) return;
    webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
      try {
        Uri uri = Uri.parse(url == null ? "" : url);
        String scheme = uri.getScheme();
        if (!("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme))) {
          try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) {}
          return;
        }
        if (${publicDownloads ? 'true' : 'false'} && Build.VERSION.SDK_INT <= Build.VERSION_CODES.P && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
          requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, 7341);
          Toast.makeText(this, "Allow storage access, then tap the download again.", Toast.LENGTH_LONG).show();
          return;
        }
        String fileName = URLUtil.guessFileName(url, contentDisposition, mimeType);
        DownloadManager.Request request = new DownloadManager.Request(uri);
        String cookies = CookieManager.getInstance().getCookie(url);
        if (cookies != null && !cookies.isEmpty()) request.addRequestHeader("Cookie", cookies);
        if (userAgent != null && !userAgent.isEmpty()) request.addRequestHeader("User-Agent", userAgent);
        if (mimeType != null && !mimeType.isEmpty()) request.setMimeType(mimeType);
        request.setTitle(fileName);
        request.setDescription("Downloading " + fileName);
        request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
        ${wifiOnly ? 'request.setAllowedNetworkTypes(DownloadManager.Request.NETWORK_WIFI);' : ''}
        if (${publicDownloads ? 'true' : 'false'}) request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName);
        else request.setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, fileName);
        DownloadManager manager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
        if (manager == null) throw new IllegalStateException("DownloadManager unavailable");
        manager.enqueue(request);
        Toast.makeText(this, "Download started", Toast.LENGTH_SHORT).show();
      } catch (Exception e) {
        Toast.makeText(this, "Download could not start", Toast.LENGTH_SHORT).show();
      }
    });
  }
`;
  if (!main.includes('installAppForgeDownloads(WebView webView)')) {
    const marker = '  private void injectAppForgeNativeSdk(WebView view, String url) {';
    if (!main.includes(marker)) throw new Error('Trusted SDK marker missing before download patch');
    main = main.replace(marker, downloadMethod + '\n' + marker);
  }
  if (!main.includes('installAppForgeDownloads(webView);')) {
    const marker = '      installAppForgeWebViewClient(webView);';
    if (!main.includes(marker)) throw new Error('WebView install marker missing before download activation');
    main = main.replace(marker, marker + '\n      installAppForgeDownloads(webView);');
  }

  if (publicDownloads) {
    const manifestPath = path.join(rootDir, 'android', 'app', 'src', 'main', 'AndroidManifest.xml');
    let manifest = fs.readFileSync(manifestPath, 'utf8');
    if (!manifest.includes('android.permission.WRITE_EXTERNAL_STORAGE')) {
      manifest = manifest.replace('<application', '    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="28" />\n\n    <application');
      fs.writeFileSync(manifestPath, manifest);
    }
  }
}

if (clipboard) {
  for (const imp of ['android.content.ClipData','android.content.ClipboardManager','android.content.Context']) bridge = ensureImport(bridge, imp);
  if (!bridge.includes('public String copyToClipboard(String text)')) {
    const method = `
  @JavascriptInterface
  public String copyToClipboard(String text) {
    if (!allowed()) return status(false, "copyToClipboard");
    activity.runOnUiThread(() -> {
      try {
        ClipboardManager manager = (ClipboardManager) activity.getSystemService(Context.CLIPBOARD_SERVICE);
        if (manager != null) manager.setPrimaryClip(ClipData.newPlainText("AppForge", text == null ? "" : text));
      } catch (Exception ignored) {}
    });
    return status(true, "copyToClipboard");
  }
`;
    const pos = bridge.lastIndexOf('\n}');
    if (pos < 0) throw new Error('GaotusNativeBridge class end marker missing');
    bridge = bridge.slice(0, pos) + method + bridge.slice(pos);
  }
}

if (appSettings) {
  bridge = ensureImport(bridge, 'android.provider.Settings');
  if (!bridge.includes('public String openAppSettings()')) {
    const method = `
  @JavascriptInterface
  public String openAppSettings() {
    if (!allowed()) return status(false, "openAppSettings");
    activity.runOnUiThread(() -> {
      try {
        Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
        intent.setData(Uri.parse("package:" + activity.getPackageName()));
        activity.startActivity(intent);
      } catch (Exception ignored) {}
    });
    return status(true, "openAppSettings");
  }
`;
    const pos = bridge.lastIndexOf('\n}');
    if (pos < 0) throw new Error('GaotusNativeBridge class end marker missing');
    bridge = bridge.slice(0, pos) + method + bridge.slice(pos);
  }
}

fs.writeFileSync(mains[0], main);
fs.writeFileSync(bridges[0], bridge);
console.log(`[AppForge] device tools downloads=${downloads}, wifiOnly=${wifiOnly}, publicDownloads=${publicDownloads}, clipboard=${clipboard}, appSettings=${appSettings}, trustedSdk=true`);
