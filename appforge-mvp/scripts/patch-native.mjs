import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient } from './lib.mjs';

const target = process.argv[2] || 'all';
const clientPath = path.join(rootDir, 'generated-client.json');
if (!fs.existsSync(clientPath)) throw new Error('generated-client.json missing. Run npm run generate first.');
const client = validateClient(readJSON(clientPath));

if (target === 'all' || target === 'android') patchAndroid(client);
if (target === 'all' || target === 'ios') patchIOS(client);

function walk(dir, predicate, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, predicate, out);
    else if (predicate(full)) out.push(full);
  }
  return out;
}

function patchAndroid(c) {
  const base = path.join(rootDir, 'android');
  if (!fs.existsSync(base)) { console.log('[AppForge] android platform not present, skipping patch'); return; }
  const mains = walk(path.join(base, 'app', 'src', 'main', 'java'), (f) => /MainActivity\.(java|kt)$/.test(f));
  if (mains.length !== 1) throw new Error(`Expected exactly one Android MainActivity, found ${mains.length}`);
  const main = mains[0];
  const original = fs.readFileSync(main, 'utf8');
  const pkg = (original.match(/package\s+([\w.]+)\s*;/) || [])[1] || c.appId;
  if (!main.endsWith('.java')) throw new Error('MVP patcher expects Capacitor Java MainActivity template');
  fs.writeFileSync(main, `package ${pkg};\n\nimport android.os.Bundle;\nimport com.getcapacitor.BridgeActivity;\n\npublic class MainActivity extends BridgeActivity {\n  @Override\n  protected void onCreate(Bundle savedInstanceState) {\n    super.onCreate(savedInstanceState);\n    if (getBridge() != null && getBridge().getWebView() != null) {\n      getBridge().getWebView().addJavascriptInterface(new GaotusNativeBridge(this), \"GaotusNativeAndroid\");\n    }\n  }\n}\n`);
  const bridgePath = path.join(path.dirname(main), 'GaotusNativeBridge.java');
  fs.writeFileSync(bridgePath, androidBridgeSource(pkg, c.mode === 'remote' ? new URL(c.url).hostname : 'localhost'));

  const manifest = path.join(base, 'app', 'src', 'main', 'AndroidManifest.xml');
  let xml = fs.readFileSync(manifest, 'utf8');
  const perms = [
    '<uses-permission android:name="android.permission.CAMERA" />',
    '<uses-permission android:name="android.permission.VIBRATE" />',
    '<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />',
    '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />'
  ];
  for (const p of perms) if (!xml.includes(p)) xml = xml.replace('<application', `    ${p}\n\n    <application`);
  fs.writeFileSync(manifest, xml);

  const gradle = path.join(base, 'app', 'build.gradle');
  let g = fs.readFileSync(gradle, 'utf8');
  g = g.replace(/versionCode\s+\d+/, `versionCode ${c.versionCode}`);
  g = g.replace(/versionName\s+"[^"]+"/, `versionName "${c.versionName}"`);
  fs.writeFileSync(gradle, g);
  console.log('[AppForge] Android native bridge patched');
}

function androidBridgeSource(pkg, allowedHost) {
  return `package ${pkg};\n\nimport android.app.Activity;\nimport android.content.Intent;\nimport android.net.Uri;\nimport android.os.Build;\nimport android.os.VibrationEffect;\nimport android.os.Vibrator;\nimport android.provider.MediaStore;\nimport android.webkit.JavascriptInterface;\nimport android.webkit.WebView;\nimport android.widget.Toast;\nimport org.json.JSONObject;\n\npublic class GaotusNativeBridge {\n  private final Activity activity;\n  private final WebView webView;\n  private final String allowedHost = "${allowedHost}";\n  public GaotusNativeBridge(Activity activity) { this.activity = activity; this.webView = activity instanceof MainActivity ? ((MainActivity) activity).getBridge().getWebView() : null; }\n\n  private boolean allowed() {\n    try {\n      if (webView == null || webView.getUrl() == null) return false;\n      Uri uri = Uri.parse(webView.getUrl());\n      String host = uri.getHost();\n      String scheme = uri.getScheme();\n      if (host == null) return false;\n      if ("localhost".equals(host) && ("capacitor".equals(scheme) || "http".equals(scheme) || "https".equals(scheme))) return true;\n      return host.equals(allowedHost) || host.endsWith("." + allowedHost);\n    } catch (Exception e) { return false; }\n  }\n\n  @JavascriptInterface\n  public String ping() { if (!allowed()) return "{\\\"ok\\\":false,\\\"error\\\":\\\"origin_not_allowed\\\"}";\n    try {\n      JSONObject o = new JSONObject();\n      o.put("ok", true); o.put("platform", "android"); o.put("bridge", "GaotusNative");\n      return o.toString();\n    } catch (Exception e) { return "{\\\"ok\\\":true}"; }\n  }\n\n  @JavascriptInterface\n  public String deviceInfo() { if (!allowed()) return "{\\\"ok\\\":false,\\\"error\\\":\\\"origin_not_allowed\\\"}";\n    try {\n      JSONObject o = new JSONObject();\n      o.put("platform", "android");\n      o.put("manufacturer", Build.MANUFACTURER);\n      o.put("model", Build.MODEL);\n      o.put("androidVersion", Build.VERSION.RELEASE);\n      o.put("sdk", Build.VERSION.SDK_INT);\n      return o.toString();\n    } catch (Exception e) { return "{\\\"platform\\\":\\\"android\\\"}"; }\n  }\n\n  @JavascriptInterface\n  public void share(String json) { if (!allowed()) return;\n    activity.runOnUiThread(() -> {\n      try {\n        JSONObject o = new JSONObject(json);\n        Intent i = new Intent(Intent.ACTION_SEND);\n        i.setType("text/plain");\n        i.putExtra(Intent.EXTRA_SUBJECT, o.optString("title", ""));\n        String text = o.optString("text", "");\n        String url = o.optString("url", "");\n        i.putExtra(Intent.EXTRA_TEXT, text + (url.isEmpty() ? "" : "\\n" + url));\n        activity.startActivity(Intent.createChooser(i, o.optString("title", "Share")));\n      } catch (Exception ignored) {}\n    });\n  }\n\n  @JavascriptInterface\n  public void openExternal(String url) { if (!allowed()) return;\n    activity.runOnUiThread(() -> {\n      try { activity.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); } catch (Exception ignored) {}\n    });\n  }\n\n  @JavascriptInterface\n  public void haptic(String type) { if (!allowed()) return;\n    activity.runOnUiThread(() -> {\n      Vibrator v = (Vibrator) activity.getSystemService(Activity.VIBRATOR_SERVICE);\n      if (v == null) return;\n      long duration = "heavy".equals(type) ? 80 : ("light".equals(type) ? 20 : 45);\n      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) v.vibrate(VibrationEffect.createOneShot(duration, VibrationEffect.DEFAULT_AMPLITUDE));\n      else v.vibrate(duration);\n    });\n  }\n\n  @JavascriptInterface\n  public void openCamera() { if (!allowed()) return;\n    activity.runOnUiThread(() -> {\n      try { activity.startActivity(new Intent(MediaStore.ACTION_IMAGE_CAPTURE)); } catch (Exception ignored) {}\n    });\n  }\n\n  @JavascriptInterface\n  public void toast(String message) { if (!allowed()) return;\n    activity.runOnUiThread(() -> Toast.makeText(activity, message, Toast.LENGTH_SHORT).show());\n  }\n}\n`;
}

function patchIOS(c) {
  const appDir = path.join(rootDir, 'ios', 'App', 'App');
  if (!fs.existsSync(appDir)) { console.log('[AppForge] ios platform not present, skipping patch'); return; }
  const scene = path.join(appDir, 'SceneDelegate.swift');
  if (!fs.existsSync(scene)) { console.log('[AppForge] SceneDelegate.swift not found; skipping iOS raw bridge patch'); return; }
  fs.writeFileSync(scene, iosSceneSource(c));

  const appDelegate = path.join(appDir, 'AppDelegate.swift');
  if (fs.existsSync(appDelegate)) {
    let s = fs.readFileSync(appDelegate, 'utf8');
    const old = 'config.delegateClass = SceneDelegate.self';
    if (s.includes(old) && !s.includes('connectingSceneSession.role == .windowApplication')) {
      s = s.replace(old, 'if connectingSceneSession.role == .windowApplication {\n            config.delegateClass = SceneDelegate.self\n        }');
      fs.writeFileSync(appDelegate, s);
    }
  }

  const plist = path.join(appDir, 'Info.plist');
  if (fs.existsSync(plist)) {
    let p = fs.readFileSync(plist, 'utf8');
    const insert = `\n\t<key>NSCameraUsageDescription</key>\n\t<string>${escapeXML(c.appName)} uses the camera when you request it.</string>\n\t<key>NSLocationWhenInUseUsageDescription</key>\n\t<string>${escapeXML(c.appName)} uses your location when you request it.</string>`;
    if (!p.includes('NSCameraUsageDescription')) p = p.replace('</dict>', `${insert}\n</dict>`);
    fs.writeFileSync(plist, p);
  }
  console.log('[AppForge] iOS native bridge patched');
}

function iosSceneSource(c) {
  const allowedHost = c.mode === 'remote' ? new URL(c.url).hostname : 'localhost';
  return `import UIKit\nimport Capacitor\nimport WebKit\n\nfinal class GaotusBridgeHandler: NSObject, WKScriptMessageHandler {\n    weak var viewController: UIViewController?\n    let allowedHost = "${allowedHost}"\n\n    init(viewController: UIViewController) {\n        self.viewController = viewController\n    }\n\n    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {\n        let originHost = message.frameInfo.request.url?.host ?? ""\n        let scheme = message.frameInfo.request.url?.scheme ?? ""\n        let localOK = originHost == "localhost" && ["capacitor", "http", "https"].contains(scheme)\n        let remoteOK = originHost == allowedHost || originHost.hasSuffix("." + allowedHost)\n        guard localOK || remoteOK else { return }\n        guard let body = message.body as? [String: Any], let action = body["action"] as? String else { return }\n        let payload = body["payload"] as? [String: Any] ?? [:]\n        DispatchQueue.main.async { [weak self] in self?.handle(action: action, payload: payload) }\n    }\n\n    private func handle(action: String, payload: [String: Any]) {\n        guard let vc = viewController else { return }\n        switch action {\n        case "share":\n            var items: [Any] = []\n            if let text = payload["text"] as? String, !text.isEmpty { items.append(text) }\n            if let urlString = payload["url"] as? String, let url = URL(string: urlString) { items.append(url) }\n            let share = UIActivityViewController(activityItems: items, applicationActivities: nil)\n            if let popover = share.popoverPresentationController { popover.sourceView = vc.view; popover.sourceRect = CGRect(x: vc.view.bounds.midX, y: vc.view.bounds.midY, width: 1, height: 1) }\n            vc.present(share, animated: true)\n        case "haptic":\n            let type = payload["type"] as? String ?? "medium"\n            let style: UIImpactFeedbackGenerator.FeedbackStyle = type == "heavy" ? .heavy : (type == "light" ? .light : .medium)\n            UIImpactFeedbackGenerator(style: style).impactOccurred()\n        case "openExternal":\n            if let value = payload["url"] as? String, let url = URL(string: value), ["http", "https"].contains(url.scheme?.lowercased() ?? "") { UIApplication.shared.open(url) }\n        case "openCamera":\n            let alert = UIAlertController(title: "Camera bridge", message: "Native camera command reached iOS. Full image callback comes in the next feature pack.", preferredStyle: .alert)\n            alert.addAction(UIAlertAction(title: "OK", style: .default))\n            vc.present(alert, animated: true)\n        case "toast":\n            let alert = UIAlertController(title: nil, message: payload["message"] as? String ?? "", preferredStyle: .alert)\n            vc.present(alert, animated: true)\n            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { alert.dismiss(animated: true) }\n        default:\n            break\n        }\n    }\n}\n\nfinal class GaotusViewController: CAPBridgeViewController {\n    private var gaotusHandler: GaotusBridgeHandler?\n\n    override func capacitorDidLoad() {\n        super.capacitorDidLoad()\n        guard let webView = bridge?.webView else { return }\n        let handler = GaotusBridgeHandler(viewController: self)\n        gaotusHandler = handler\n        webView.configuration.userContentController.add(handler, name: "gaotusNative")\n    }\n\n    deinit {\n        bridge?.webView?.configuration.userContentController.removeScriptMessageHandler(forName: "gaotusNative")\n    }\n}\n\nclass SceneDelegate: UIResponder, UIWindowSceneDelegate {\n    var window: UIWindow?\n\n    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {\n        guard session.role == .windowApplication, let windowScene = scene as? UIWindowScene else { return }\n        let window = UIWindow(windowScene: windowScene)\n        window.rootViewController = GaotusViewController()\n        self.window = window\n        window.makeKeyAndVisible()\n    }\n}\n`;
}

function escapeXML(v) { return String(v).replace(/[<>&'\"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;',"'":'&apos;','"':'&quot;'}[c])); }
