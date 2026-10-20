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
const ui = client.uiNavigation || {};
const appSettings = client.appSettings || {};
const headerEnabled = ui.header_enabled === true;
const bottomEnabled = ui.bottom_nav_enabled === true;
const floatingEnabled = ui.floating_button_enabled === true && String(ui.floating_button_url || '').trim() !== '';
const pullRefresh = appSettings.pull_to_refresh === true;
const pageLoader = appSettings.page_loader === true;
if (!headerEnabled && !bottomEnabled && !floatingEnabled && !pullRefresh && !pageLoader) {
  console.log('[AppForge] native UI extras disabled; no Android UI patch required');
  process.exit(0);
}

const files = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
if (files.length !== 1) throw new Error(`Expected one MainActivity.java, found ${files.length}`);
const file = files[0];
let src = fs.readFileSync(file, 'utf8');

const color = (v, fallback) => /^#[0-9a-fA-F]{6}$/.test(String(v || '')) ? String(v) : fallback;
const headerTitle = String(ui.header_title || client.appName || 'App');
const headerBg = color(ui.header_background, '#111827');
const headerText = color(ui.header_text, '#ffffff');
const floatingLabel = String(ui.floating_button_label || 'Open');
const floatingUrl = String(ui.floating_button_url || '');
const items = Array.isArray(ui.bottom_nav_items) ? ui.bottom_nav_items.slice(0, 5) : [];

if (!src.includes('import android.view.ViewGroup;')) {
  const swipeImport = pullRefresh ? 'import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;\n' : '';
  src = src.replace(
    'import android.view.View;\n',
    `import android.view.View;\nimport android.view.ViewGroup;\nimport android.view.Gravity;\nimport android.widget.LinearLayout;\nimport android.widget.FrameLayout;\nimport android.widget.TextView;\nimport android.widget.Button;\nimport android.widget.ProgressBar;\n${swipeImport}`
  );
}

const gradlePath = path.join(rootDir, 'android', 'app', 'build.gradle');
let gradle = fs.readFileSync(gradlePath, 'utf8');
if (pullRefresh && !gradle.includes('androidx.swiperefreshlayout:swiperefreshlayout')) {
  const marker = `implementation project(':capacitor-cordova-android-plugins')`;
  if (!gradle.includes(marker)) throw new Error('Capacitor app dependency marker missing for swipe refresh');
  gradle = gradle.replace(marker, `${marker}\n    implementation 'androidx.swiperefreshlayout:swiperefreshlayout:1.1.0'`);
  fs.writeFileSync(gradlePath, gradle);
}

const itemBuilders = items.map((item, index) => {
  const label = JSON.stringify(String(item?.label || `Item ${index + 1}`));
  const target = JSON.stringify(String(item?.url || '/'));
  return `
    TextView nav${index} = new TextView(this);
    nav${index}.setText(${label});
    nav${index}.setGravity(Gravity.CENTER);
    nav${index}.setTextColor(Color.parseColor("#334155"));
    nav${index}.setTextSize(12f);
    nav${index}.setPadding(dp(6), dp(6), dp(6), dp(6));
    nav${index}.setOnClickListener(v -> webView.loadUrl(resolveAppForgeTarget(${target})));
    bottom.addView(nav${index}, new LinearLayout.LayoutParams(0, dp(58), 1f));`;
}).join('\n');

const swipeField = pullRefresh ? '  private SwipeRefreshLayout appForgeRefreshLayout;\n' : '';
const refreshStop = pullRefresh ? '    if (!loading && appForgeRefreshLayout != null) appForgeRefreshLayout.setRefreshing(false);\n' : '';

const method = `
${swipeField}  private ProgressBar appForgePageLoader;

  private int dp(int value) {
    return Math.round(value * getResources().getDisplayMetrics().density);
  }

  private String resolveAppForgeTarget(String target) {
    if (target == null || target.isEmpty()) return APPFORGE_START_URL;
    if (target.startsWith("http://") || target.startsWith("https://")) return target;
    try {
      Uri base = Uri.parse(APPFORGE_START_URL);
      String origin = base.getScheme() + "://" + base.getAuthority();
      return origin + (target.startsWith("/") ? target : "/" + target);
    } catch (Exception ignored) { return APPFORGE_START_URL; }
  }

  public void setAppForgeLoading(boolean loading) {
    if (appForgePageLoader != null) appForgePageLoader.setVisibility(loading ? View.VISIBLE : View.GONE);
${refreshStop}  }

  private void applyNativeChrome(WebView webView) {
    if (webView == null) return;
    ViewGroup parent = (ViewGroup) webView.getParent();
    if (parent == null) return;
    int index = parent.indexOfChild(webView);
    ViewGroup.LayoutParams originalParams = webView.getLayoutParams();
    parent.removeView(webView);

    LinearLayout shell = new LinearLayout(this);
    shell.setOrientation(LinearLayout.VERTICAL);
    shell.setBackgroundColor(Color.WHITE);

    ${headerEnabled ? `TextView header = new TextView(this);
    header.setText(${JSON.stringify(headerTitle)});
    header.setTextColor(Color.parseColor(${JSON.stringify(headerText)}));
    header.setBackgroundColor(Color.parseColor(${JSON.stringify(headerBg)}));
    header.setTextSize(18f);
    header.setGravity(Gravity.CENTER_VERTICAL);
    header.setPadding(dp(18), 0, dp(18), 0);
    shell.addView(header, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(56)));` : ''}

    FrameLayout body = new FrameLayout(this);
    ${pullRefresh ? `appForgeRefreshLayout = new SwipeRefreshLayout(this);
    appForgeRefreshLayout.addView(webView, new SwipeRefreshLayout.LayoutParams(SwipeRefreshLayout.LayoutParams.MATCH_PARENT, SwipeRefreshLayout.LayoutParams.MATCH_PARENT));
    appForgeRefreshLayout.setOnRefreshListener(webView::reload);
    body.addView(appForgeRefreshLayout, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));` : `body.addView(webView, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));`}

    ${pageLoader ? `appForgePageLoader = new ProgressBar(this);
    FrameLayout.LayoutParams loaderParams = new FrameLayout.LayoutParams(dp(44), dp(44));
    loaderParams.gravity = Gravity.CENTER;
    body.addView(appForgePageLoader, loaderParams);` : ''}

    ${floatingEnabled ? `Button floating = new Button(this);
    floating.setText(${JSON.stringify(floatingLabel)});
    floating.setTextColor(Color.WHITE);
    floating.setBackgroundColor(Color.parseColor(${JSON.stringify(client.accentColor || '#fbbf24')}));
    floating.setOnClickListener(v -> webView.loadUrl(resolveAppForgeTarget(${JSON.stringify(floatingUrl)})));
    FrameLayout.LayoutParams floatParams = new FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, dp(52));
    floatParams.gravity = Gravity.BOTTOM | Gravity.END;
    floatParams.setMargins(dp(16), dp(16), dp(16), dp(16));
    body.addView(floating, floatParams);` : ''}

    shell.addView(body, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

    ${bottomEnabled ? `LinearLayout bottom = new LinearLayout(this);
    bottom.setOrientation(LinearLayout.HORIZONTAL);
    bottom.setGravity(Gravity.CENTER);
    bottom.setBackgroundColor(Color.WHITE);
    bottom.setPadding(dp(6), 0, dp(6), 0);
${itemBuilders || `    TextView home = new TextView(this);
    home.setText("Home");
    home.setGravity(Gravity.CENTER);
    home.setOnClickListener(v -> webView.loadUrl(resolveAppForgeTarget("/")));
    bottom.addView(home, new LinearLayout.LayoutParams(0, dp(58), 1f));`}
    shell.addView(bottom, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(58)));` : ''}

    parent.addView(shell, index, originalParams);
  }
`;

const marker = '  @Override\n  protected void onCreate(Bundle savedInstanceState) {';
if (!src.includes(marker)) throw new Error('MainActivity onCreate marker not found for native UI patch');
src = src.replace(marker, method + '\n' + marker);
src = src.replace('      enforceConfiguredSite(webView);\n', '      enforceConfiguredSite(webView);\n      applyNativeChrome(webView);\n');

fs.writeFileSync(file, src);
console.log(`[AppForge] native Android UI: header=${headerEnabled}, bottomNav=${bottomEnabled}, pullRefresh=${pullRefresh}, loader=${pageLoader}, floating=${floatingEnabled}`);
