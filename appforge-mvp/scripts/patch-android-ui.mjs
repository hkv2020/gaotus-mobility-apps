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
const color = (v, fallback) => /^#[0-9a-fA-F]{6}$/.test(String(v || '')) ? String(v) : fallback;
const bool = (v) => v === true;
const glyph = (key) => ({home:'⌂',search:'⌕',user:'●',account:'●',cart:'▣',phone:'☎',info:'ⓘ',settings:'⚙',link:'↗',menu:'☰',heart:'♥',bell:'●',mail:'✉',chat:'✦',more:'⋯'}[String(key || '').toLowerCase()] || '•');

async function prepareFloatingDrawable(url) {
  const value = String(url || '').trim();
  if (!/^https:\/\//i.test(value)) return false;
  try {
    const parsed = new URL(value);
    if (!parsed.hostname || /^(localhost|127\.|0\.0\.0\.0$|\[?::1\]?$)/i.test(parsed.hostname)) return false;
    const response = await fetch(value, { signal: AbortSignal.timeout(12000), redirect: 'follow' });
    if (!response.ok) return false;
    const type = String(response.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
    const ext = type === 'image/png' ? 'png' : (type === 'image/jpeg' ? 'jpg' : (type === 'image/webp' ? 'webp' : ''));
    if (!ext) return false;
    const body = Buffer.from(await response.arrayBuffer());
    if (body.length < 1 || body.length > 3 * 1024 * 1024) return false;
    const dir = path.join(rootDir, 'android', 'app', 'src', 'main', 'res', 'drawable');
    fs.mkdirSync(dir, { recursive: true });
    for (const old of fs.readdirSync(dir)) if (/^appforge_floating_icon\.(png|jpg|jpeg|webp)$/i.test(old)) fs.rmSync(path.join(dir, old), { force: true });
    fs.writeFileSync(path.join(dir, `appforge_floating_icon.${ext}`), body);
    return true;
  } catch {
    return false;
  }
}

const client = validateClient(readJSON(path.join(rootDir, 'generated-client.json')));
const ui = client.uiNavigation || {};
const appSettings = client.appSettings || {};
const headerEnabled = bool(ui.header_enabled);
const bottomEnabled = bool(ui.bottom_nav_enabled);
const floatingEnabled = bool(ui.floating_button_enabled) && String(ui.floating_button_url || '').trim() !== '';
const sidebarEnabled = bool(ui.sidebar_enabled);
const pullRefresh = bool(appSettings.pull_to_refresh);
const pageLoader = bool(appSettings.page_loader);
const loaderType = ['progress','circular','lottie'].includes(ui.page_loader_type) ? ui.page_loader_type : 'circular';
if (!headerEnabled && !bottomEnabled && !floatingEnabled && !sidebarEnabled && !pullRefresh && !pageLoader) {
  console.log('[AppForge] native UI extras disabled; no Android UI patch required');
  process.exit(0);
}

const files = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
if (files.length !== 1) throw new Error(`Expected one MainActivity.java, found ${files.length}`);
const file = files[0];
let src = fs.readFileSync(file, 'utf8');
const floatingIconUrl = String(ui.floating_button_icon_url || '').trim();
const floatingDrawable = floatingEnabled && floatingIconUrl ? await prepareFloatingDrawable(floatingIconUrl) : false;

if (floatingEnabled && floatingIconUrl && !floatingDrawable) throw new Error('Floating Button custom icon could not be downloaded as HTTPS PNG/JPEG/WebP');

for (const imp of [
  'android.content.res.ColorStateList', 'android.graphics.Color', 'android.graphics.drawable.GradientDrawable',
  'android.net.Uri', 'android.view.Gravity', 'android.view.View', 'android.view.ViewGroup',
  'android.webkit.WebView', 'android.widget.EditText', 'android.widget.FrameLayout', 'android.widget.ImageView',
  'android.widget.LinearLayout', 'android.widget.ProgressBar', 'android.widget.TextView'
]) src = ensureImport(src, imp);
if (floatingDrawable) src = ensureImport(src, 'android.graphics.drawable.Drawable');
if (pullRefresh) src = ensureImport(src, 'androidx.swiperefreshlayout.widget.SwipeRefreshLayout');
if (pageLoader && loaderType === 'lottie') src = ensureImport(src, 'com.airbnb.lottie.LottieAnimationView');

const gradlePath = path.join(rootDir, 'android', 'app', 'build.gradle');
let gradle = fs.readFileSync(gradlePath, 'utf8');
const depMarker = `implementation project(':capacitor-cordova-android-plugins')`;
if ((pullRefresh || (pageLoader && loaderType === 'lottie')) && !gradle.includes(depMarker)) throw new Error('Capacitor app dependency marker missing for AppForge UI dependencies');
if (pullRefresh && !gradle.includes('androidx.swiperefreshlayout:swiperefreshlayout')) gradle = gradle.replace(depMarker, `${depMarker}\n    implementation 'androidx.swiperefreshlayout:swiperefreshlayout:1.1.0'`);
if (pageLoader && loaderType === 'lottie' && !gradle.includes('com.airbnb.android:lottie')) gradle = gradle.replace(depMarker, `${depMarker}\n    implementation 'com.airbnb.android:lottie:6.4.1'`);
fs.writeFileSync(gradlePath, gradle);

const headerTemplate = ['simple_dark','side_logo_dark','simple_light','floating_dark','right_logo_dark','logo_search'].includes(ui.header_template) ? ui.header_template : 'simple_dark';
const headerTitle = String(ui.header_title || client.appName || 'App').slice(0, 80);
const headerBg = color(ui.header_background, headerTemplate === 'simple_light' || headerTemplate === 'logo_search' ? '#ffffff' : '#111827');
const headerText = color(ui.header_text, headerTemplate === 'simple_light' || headerTemplate === 'logo_search' ? '#111827' : '#ffffff');
const headerSearchUrl = String(ui.header_search_url || '/?s={query}').slice(0, 500);
const bottomDefault = color(ui.bottom_nav_default_color, '#64748b');
const bottomActive = color(ui.bottom_nav_active_color, client.accentColor || '#fbbf24');
const bottomBg = color(ui.bottom_nav_background_color, '#ffffff');
const floatingLabel = String(ui.floating_button_label || '').slice(0, 40);
const floatingUrl = String(ui.floating_button_url || '');
const floatingIcon = glyph(ui.floating_button_icon || 'link');
const floatingBg = color(ui.floating_button_background, client.accentColor || '#fbbf24');
const floatingText = color(ui.floating_button_text, '#111827');
const floatingPosition = ui.floating_button_position === 'left' ? 'left' : 'right';
const floatingShape = ui.floating_button_shape === 'square' ? 'square' : 'circular';
const sidebarTemplate = ['vertical_cards','submenus','cards','single'].includes(ui.sidebar_template) ? ui.sidebar_template : 'single';
const sidebarBg = color(ui.sidebar_background, '#ffffff');
const sidebarText = color(ui.sidebar_text, '#111827');
const pullColor = color(ui.pull_refresh_color, client.accentColor || '#fbbf24');
const loaderColor = color(ui.page_loader_color, client.accentColor || '#fbbf24');
const loaderBg = color(ui.page_loader_background, '#ffffff');
const lottieUrl = String(ui.page_loader_lottie_url || '').slice(0, 1000);
const items = Array.isArray(ui.bottom_nav_items) ? ui.bottom_nav_items.slice(0, 5) : [];
const sidebarItems = Array.isArray(ui.sidebar_items) ? ui.sidebar_items.slice(0, 12) : [];

const bottomBuilders = items.map((item, index) => {
  const label = JSON.stringify(String(item?.label || `Item ${index + 1}`));
  const target = JSON.stringify(String(item?.url || '/'));
  const icon = JSON.stringify(glyph(item?.icon || 'link'));
  return `    addAppForgeBottomItem(bottom, ${label}, ${target}, ${icon}, webView, ${index === 0 ? 'true' : 'false'});`;
}).join('\n');
const sidebarBuilders = sidebarItems.map((item, index) => {
  const label = JSON.stringify(String(item?.label || `Item ${index + 1}`));
  const target = JSON.stringify(String(item?.url || '/'));
  const icon = JSON.stringify(glyph(item?.icon || 'link'));
  return `    addAppForgeSidebarItem(panel, ${label}, ${target}, ${icon}, webView);`;
}).join('\n');

const swipeField = pullRefresh ? '  private SwipeRefreshLayout appForgeRefreshLayout;\n' : '';
const lottieField = pageLoader && loaderType === 'lottie' ? '  private LottieAnimationView appForgeLottieLoader;\n' : '';
const refreshStop = pullRefresh ? '    if (!loading && appForgeRefreshLayout != null) appForgeRefreshLayout.setRefreshing(false);\n' : '';
const lottieToggle = pageLoader && loaderType === 'lottie' ? '    if (appForgeLottieLoader != null) { if (loading) appForgeLottieLoader.playAnimation(); else appForgeLottieLoader.pauseAnimation(); }\n' : '';

const method = `
${swipeField}${lottieField}  private View appForgeLoaderContainer;
  private LinearLayout appForgeSidebarPanel;
  private View appForgeSidebarScrim;

  private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

  private String resolveAppForgeTarget(String target) {
    if (target == null || target.isEmpty()) return APPFORGE_START_URL;
    if (target.startsWith("http://") || target.startsWith("https://")) return target;
    try {
      Uri base = Uri.parse(APPFORGE_START_URL);
      String origin = base.getScheme() + "://" + base.getAuthority();
      return origin + (target.startsWith("/") ? target : "/" + target);
    } catch (Exception ignored) { return APPFORGE_START_URL; }
  }

  private GradientDrawable appForgeBackground(String value, boolean circle, float radius) {
    GradientDrawable d = new GradientDrawable();
    d.setColor(Color.parseColor(value));
    if (circle) d.setShape(GradientDrawable.OVAL); else d.setCornerRadius(dp((int) radius));
    return d;
  }

  private TextView appForgeAction(String text, int textColor) {
    TextView v = new TextView(this);
    v.setText(text); v.setTextColor(textColor); v.setTextSize(18f); v.setGravity(Gravity.CENTER);
    v.setPadding(dp(12), 0, dp(12), 0); v.setMinWidth(dp(44));
    return v;
  }

  private void selectAppForgeBottom(LinearLayout bottom, View selected) {
    for (int i = 0; i < bottom.getChildCount(); i++) {
      View child = bottom.getChildAt(i);
      int color = child == selected ? Color.parseColor(${JSON.stringify(bottomActive)}) : Color.parseColor(${JSON.stringify(bottomDefault)});
      if (child instanceof LinearLayout) {
        LinearLayout cell = (LinearLayout) child;
        for (int j = 0; j < cell.getChildCount(); j++) if (cell.getChildAt(j) instanceof TextView) ((TextView) cell.getChildAt(j)).setTextColor(color);
      }
    }
  }

  private void addAppForgeBottomItem(LinearLayout bottom, String label, String target, String icon, WebView webView, boolean active) {
    LinearLayout cell = new LinearLayout(this);
    cell.setOrientation(LinearLayout.VERTICAL); cell.setGravity(Gravity.CENTER); cell.setPadding(dp(4), dp(5), dp(4), dp(4));
    TextView iconView = new TextView(this); iconView.setText(icon); iconView.setTextSize(19f); iconView.setGravity(Gravity.CENTER);
    TextView labelView = new TextView(this); labelView.setText(label); labelView.setTextSize(10f); labelView.setGravity(Gravity.CENTER); labelView.setSingleLine(true);
    int tint = Color.parseColor(active ? ${JSON.stringify(bottomActive)} : ${JSON.stringify(bottomDefault)});
    iconView.setTextColor(tint); labelView.setTextColor(tint);
    cell.addView(iconView, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
    cell.addView(labelView, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(20)));
    cell.setOnClickListener(v -> { selectAppForgeBottom(bottom, cell); webView.loadUrl(resolveAppForgeTarget(target)); });
    bottom.addView(cell, new LinearLayout.LayoutParams(0, dp(62), 1f));
  }

  private void toggleAppForgeSidebar(boolean show) {
    if (appForgeSidebarPanel == null || appForgeSidebarScrim == null) return;
    appForgeSidebarPanel.setVisibility(show ? View.VISIBLE : View.GONE);
    appForgeSidebarScrim.setVisibility(show ? View.VISIBLE : View.GONE);
  }

  private void addAppForgeSidebarItem(LinearLayout panel, String label, String target, String icon, WebView webView) {
    TextView item = new TextView(this);
    item.setText(icon + "   " + label); item.setTextColor(Color.parseColor(${JSON.stringify(sidebarText)})); item.setTextSize(15f); item.setGravity(Gravity.CENTER_VERTICAL);
    item.setPadding(dp(16), dp(12), dp(16), dp(12));
    ${sidebarTemplate === 'vertical_cards' || sidebarTemplate === 'cards' ? `item.setBackground(appForgeBackground("#f8fafc", false, 12));` : ''}
    item.setOnClickListener(v -> { toggleAppForgeSidebar(false); webView.loadUrl(resolveAppForgeTarget(target)); });
    LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    p.setMargins(dp(10), dp(4), dp(10), dp(4)); panel.addView(item, p);
  }

  private View createAppForgeHeader(WebView webView) {
    LinearLayout header = new LinearLayout(this);
    header.setOrientation(LinearLayout.HORIZONTAL); header.setGravity(Gravity.CENTER_VERTICAL); header.setPadding(dp(8), 0, dp(8), 0);
    header.setBackgroundColor(Color.parseColor(${JSON.stringify(headerBg)}));
    int textColor = Color.parseColor(${JSON.stringify(headerText)});

    TextView backAction = appForgeAction("‹", textColor);
    backAction.setOnClickListener(v -> { if (webView.canGoBack()) webView.goBack(); });
    TextView menuAction = appForgeAction("☰", textColor);
    menuAction.setOnClickListener(v -> toggleAppForgeSidebar(true));
    TextView reloadAction = appForgeAction("↻", textColor);
    reloadAction.setOnClickListener(v -> webView.reload());

    ImageView logo = new ImageView(this);
    logo.setImageResource(getApplicationInfo().icon);
    logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
    logo.setPadding(dp(4), dp(8), dp(4), dp(8));

    TextView title = new TextView(this);
    title.setText(${JSON.stringify(headerTitle)});
    title.setTextColor(textColor);
    title.setTextSize(15f);
    title.setGravity(Gravity.CENTER_VERTICAL);
    title.setSingleLine(true);

    if (${JSON.stringify(headerTemplate)}.equals("simple_dark") || ${JSON.stringify(headerTemplate)}.equals("simple_light") || ${JSON.stringify(headerTemplate)}.equals("floating_dark")) {
      header.addView(backAction, new LinearLayout.LayoutParams(dp(44), dp(54)));
      title.setGravity(Gravity.CENTER);
      header.addView(title, new LinearLayout.LayoutParams(0, dp(54), 1f));
      header.addView(reloadAction, new LinearLayout.LayoutParams(dp(44), dp(54)));
    } else if (${JSON.stringify(headerTemplate)}.equals("right_logo_dark")) {
      header.addView(backAction, new LinearLayout.LayoutParams(dp(44), dp(54)));
      title.setGravity(Gravity.END | Gravity.CENTER_VERTICAL);
      header.addView(title, new LinearLayout.LayoutParams(0, dp(54), 1f));
      header.addView(logo, new LinearLayout.LayoutParams(dp(46), dp(54)));
    } else {
      ${sidebarEnabled ? `header.addView(menuAction, new LinearLayout.LayoutParams(dp(48), dp(54)));` : `header.addView(backAction, new LinearLayout.LayoutParams(dp(44), dp(54)));`}
      header.addView(logo, new LinearLayout.LayoutParams(dp(44), dp(54)));
      header.addView(title, new LinearLayout.LayoutParams(0, dp(54), 1f));
      if (${JSON.stringify(headerTemplate)}.equals("logo_search")) {
        TextView search = appForgeAction("⌕", textColor);
        search.setOnClickListener(v -> {
          EditText input = new EditText(this); input.setSingleLine(true); input.setHint("Search");
          new android.app.AlertDialog.Builder(this).setTitle("Search").setView(input).setNegativeButton("Cancel", null).setPositiveButton("Go", (d, w) -> {
            String q = Uri.encode(String.valueOf(input.getText()));
            String target = ${JSON.stringify(headerSearchUrl)}.replace("{query}", q);
            webView.loadUrl(resolveAppForgeTarget(target));
          }).show();
        });
        header.addView(search, new LinearLayout.LayoutParams(dp(48), dp(54)));
      } else {
        header.addView(reloadAction, new LinearLayout.LayoutParams(dp(44), dp(54)));
      }
    }
    return header;
  }

  private void installAppForgeSidebar(FrameLayout body, WebView webView) {
    ${sidebarEnabled ? `appForgeSidebarScrim = new View(this); appForgeSidebarScrim.setBackgroundColor(0x66000000); appForgeSidebarScrim.setVisibility(View.GONE); appForgeSidebarScrim.setOnClickListener(v -> toggleAppForgeSidebar(false)); body.addView(appForgeSidebarScrim, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
    appForgeSidebarPanel = new LinearLayout(this); appForgeSidebarPanel.setOrientation(LinearLayout.VERTICAL); appForgeSidebarPanel.setBackgroundColor(Color.parseColor(${JSON.stringify(sidebarBg)})); appForgeSidebarPanel.setPadding(dp(4), dp(18), dp(4), dp(18)); appForgeSidebarPanel.setVisibility(View.GONE);
    TextView heading = new TextView(this); heading.setText(${JSON.stringify(client.appName)}); heading.setTextColor(Color.parseColor(${JSON.stringify(sidebarText)})); heading.setTextSize(19f); heading.setPadding(dp(16), dp(8), dp(16), dp(14)); appForgeSidebarPanel.addView(heading);
${sidebarBuilders || `    addAppForgeSidebarItem(appForgeSidebarPanel, "Home", "/", "⌂", webView);`}
    FrameLayout.LayoutParams panelParams = new FrameLayout.LayoutParams(dp(288), FrameLayout.LayoutParams.MATCH_PARENT); panelParams.gravity = Gravity.START; body.addView(appForgeSidebarPanel, panelParams);
    ${!headerEnabled ? `TextView menuFab = appForgeAction("☰", Color.WHITE); menuFab.setBackground(appForgeBackground(${JSON.stringify(client.themeColor || '#111827')}, true, 24)); menuFab.setOnClickListener(v -> toggleAppForgeSidebar(true)); FrameLayout.LayoutParams mp = new FrameLayout.LayoutParams(dp(48), dp(48)); mp.gravity = Gravity.TOP | Gravity.START; mp.setMargins(dp(12), dp(12), 0, 0); body.addView(menuFab, mp);` : ''}` : ''}
  }

  public void setAppForgeLoading(boolean loading) {
    if (appForgeLoaderContainer != null) appForgeLoaderContainer.setVisibility(loading ? View.VISIBLE : View.GONE);
${refreshStop}${lottieToggle}  }

  private void installAppForgeLoader(FrameLayout body) {
    ${pageLoader ? `FrameLayout overlay = new FrameLayout(this); overlay.setBackgroundColor(Color.parseColor(${JSON.stringify(loaderBg)})); overlay.setClickable(false); overlay.setVisibility(View.GONE); appForgeLoaderContainer = overlay;
    ${loaderType === 'progress' ? `ProgressBar bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal); bar.setIndeterminate(true); bar.setIndeterminateTintList(ColorStateList.valueOf(Color.parseColor(${JSON.stringify(loaderColor)}))); FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, dp(4)); lp.gravity = Gravity.TOP; overlay.addView(bar, lp);` : loaderType === 'lottie' ? `appForgeLottieLoader = new LottieAnimationView(this); appForgeLottieLoader.setRepeatCount(-1); appForgeLottieLoader.setRepeatMode(1); ${lottieUrl ? `appForgeLottieLoader.setAnimationFromUrl(${JSON.stringify(lottieUrl)});` : ''} FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(dp(92), dp(92)); lp.gravity = Gravity.CENTER; overlay.addView(appForgeLottieLoader, lp);` : `ProgressBar spinner = new ProgressBar(this); spinner.setIndeterminateTintList(ColorStateList.valueOf(Color.parseColor(${JSON.stringify(loaderColor)}))); FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(dp(50), dp(50)); lp.gravity = Gravity.CENTER; overlay.addView(spinner, lp);`}
    body.addView(overlay, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));` : ''}
  }

  private void applyNativeChrome(WebView webView) {
    if (webView == null) return;
    ViewGroup parent = (ViewGroup) webView.getParent(); if (parent == null) return;
    int index = parent.indexOfChild(webView); ViewGroup.LayoutParams originalParams = webView.getLayoutParams(); parent.removeView(webView);
    LinearLayout shell = new LinearLayout(this); shell.setOrientation(LinearLayout.VERTICAL); shell.setBackgroundColor(Color.WHITE);
    ${headerEnabled ? `View header = createAppForgeHeader(webView); LinearLayout.LayoutParams hp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(56)); ${headerTemplate === 'floating_dark' ? `hp.setMargins(dp(8), dp(6), dp(8), dp(4));` : ''} shell.addView(header, hp);` : ''}
    FrameLayout body = new FrameLayout(this);
    ${pullRefresh ? `appForgeRefreshLayout = new SwipeRefreshLayout(this); appForgeRefreshLayout.setColorSchemeColors(Color.parseColor(${JSON.stringify(pullColor)})); appForgeRefreshLayout.addView(webView, new SwipeRefreshLayout.LayoutParams(SwipeRefreshLayout.LayoutParams.MATCH_PARENT, SwipeRefreshLayout.LayoutParams.MATCH_PARENT)); appForgeRefreshLayout.setOnRefreshListener(webView::reload); body.addView(appForgeRefreshLayout, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));` : `body.addView(webView, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));`}
    installAppForgeLoader(body);
    ${floatingEnabled ? `TextView floating = new TextView(this); floating.setText(${JSON.stringify(floatingDrawable ? floatingLabel : (floatingIcon + (floatingLabel ? '  ' + floatingLabel : ''))) }); floating.setTextColor(Color.parseColor(${JSON.stringify(floatingText)})); floating.setTextSize(14f); floating.setGravity(Gravity.CENTER); floating.setPadding(dp(16), 0, dp(16), 0); ${floatingDrawable ? `Drawable fd = getResources().getDrawable(R.drawable.appforge_floating_icon, getTheme()); fd.setBounds(0, 0, dp(24), dp(24)); floating.setCompoundDrawables(fd, null, null, null); floating.setCompoundDrawablePadding(dp(8));` : ''} floating.setBackground(appForgeBackground(${JSON.stringify(floatingBg)}, ${floatingShape === 'circular' ? 'true' : 'false'}, ${floatingShape === 'square' ? '12' : '28'})); floating.setElevation(dp(8)); floating.setOnClickListener(v -> webView.loadUrl(resolveAppForgeTarget(${JSON.stringify(floatingUrl)}))); FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(${floatingShape === 'circular' && !floatingLabel ? 'dp(56)' : 'FrameLayout.LayoutParams.WRAP_CONTENT'}, dp(56)); fp.gravity = Gravity.BOTTOM | ${floatingPosition === 'left' ? 'Gravity.START' : 'Gravity.END'}; fp.setMargins(dp(16), dp(16), dp(16), dp(18)); body.addView(floating, fp);` : ''}
    installAppForgeSidebar(body, webView);
    shell.addView(body, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
    ${bottomEnabled ? `LinearLayout bottom = new LinearLayout(this); bottom.setOrientation(LinearLayout.HORIZONTAL); bottom.setGravity(Gravity.CENTER); bottom.setBackgroundColor(Color.parseColor(${JSON.stringify(bottomBg)})); bottom.setPadding(dp(4), 0, dp(4), 0);\n${bottomBuilders || `    addAppForgeBottomItem(bottom, "Home", "/", "⌂", webView, true);`}\n    shell.addView(bottom, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(62)));` : ''}
    parent.addView(shell, index, originalParams);
  }
`;

const marker = '  @Override\n  protected void onCreate(Bundle savedInstanceState) {';
if (!src.includes(marker)) throw new Error('MainActivity onCreate marker not found for native UI patch');
src = src.replace(marker, method + '\n' + marker);
if (!src.includes('      enforceConfiguredSite(webView);\n')) throw new Error('Configured site guard call missing for native UI patch');
src = src.replace('      enforceConfiguredSite(webView);\n', '      enforceConfiguredSite(webView);\n      applyNativeChrome(webView);\n');
fs.writeFileSync(file, src);
console.log(`[AppForge] native UI header=${headerEnabled}:${headerTemplate}, bottom=${bottomEnabled}, sidebar=${sidebarEnabled}:${sidebarTemplate}, pullRefresh=${pullRefresh}, loader=${pageLoader}:${loaderType}, floating=${floatingEnabled}, floatingDrawable=${floatingDrawable}`);
