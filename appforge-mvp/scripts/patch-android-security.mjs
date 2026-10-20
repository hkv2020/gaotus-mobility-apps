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
const security = client.security || {};
const device = client.deviceHardware || {};
const biometric = security.biometric_lock === true;
const secure = security.prevent_screenshots === true;
const keepAwake = device.keep_screen_on === true;
if (!biometric && !secure && !keepAwake) {
  console.log('[AppForge] security/device window extras disabled');
  process.exit(0);
}

const files = walk(path.join(rootDir, 'android', 'app', 'src', 'main', 'java'));
if (files.length !== 1) throw new Error(`Expected one MainActivity.java, found ${files.length}`);
const file = files[0];
let src = fs.readFileSync(file, 'utf8');

if (biometric) {
  const gradlePath = path.join(rootDir, 'android', 'app', 'build.gradle');
  let gradle = fs.readFileSync(gradlePath, 'utf8');
  if (!gradle.includes('androidx.biometric:biometric')) {
    const marker = `implementation project(':capacitor-cordova-android-plugins')`;
    if (!gradle.includes(marker)) throw new Error('Capacitor app dependency marker missing for biometric');
    gradle = gradle.replace(marker, `${marker}\n    implementation 'androidx.biometric:biometric:1.1.0'`);
    fs.writeFileSync(gradlePath, gradle);
  }
  if (!src.includes('import androidx.biometric.BiometricManager;')) {
    src = src.replace('import androidx.activity.OnBackPressedCallback;\n', 'import androidx.activity.OnBackPressedCallback;\nimport androidx.biometric.BiometricManager;\nimport androidx.biometric.BiometricPrompt;\nimport androidx.core.content.ContextCompat;\nimport java.util.concurrent.Executor;\n');
  }
  const method = `
  private void requireAppForgeBiometric(WebView webView) {
    if (webView == null) return;
    final int authenticators = BiometricManager.Authenticators.BIOMETRIC_STRONG | BiometricManager.Authenticators.DEVICE_CREDENTIAL;
    BiometricManager manager = BiometricManager.from(this);
    if (manager.canAuthenticate(authenticators) != BiometricManager.BIOMETRIC_SUCCESS) return;
    webView.setVisibility(View.INVISIBLE);
    Executor executor = ContextCompat.getMainExecutor(this);
    BiometricPrompt prompt = new BiometricPrompt(this, executor, new BiometricPrompt.AuthenticationCallback() {
      @Override
      public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result) {
        super.onAuthenticationSucceeded(result);
        webView.setVisibility(View.VISIBLE);
      }
      @Override
      public void onAuthenticationError(int errorCode, CharSequence errString) {
        super.onAuthenticationError(errorCode, errString);
        finish();
      }
    });
    BiometricPrompt.PromptInfo info = new BiometricPrompt.PromptInfo.Builder()
      .setTitle(${JSON.stringify(`Unlock ${client.appName}`)})
      .setSubtitle("Authenticate to continue")
      .setAllowedAuthenticators(authenticators)
      .build();
    prompt.authenticate(info);
  }
`;
  const marker = '  @Override\n  protected void onCreate(Bundle savedInstanceState) {';
  if (!src.includes(marker)) throw new Error('MainActivity marker missing for biometric patch');
  src = src.replace(marker, method + '\n' + marker);
}

let windowCode = '';
if (secure) windowCode += '    getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);\n';
if (keepAwake) windowCode += '    getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n';
if (windowCode && !src.includes('APPFORGE_WINDOW_SECURITY')) {
  src = src.replace('    super.onCreate(savedInstanceState);', `    super.onCreate(savedInstanceState);\n    // APPFORGE_WINDOW_SECURITY\n${windowCode.trimEnd()}`);
}
if (biometric && !src.includes('requireAppForgeBiometric(webView);')) {
  if (!src.includes('      enforceConfiguredSite(webView);')) throw new Error('Configured-site marker missing for biometric call');
  src = src.replace('      enforceConfiguredSite(webView);\n', '      enforceConfiguredSite(webView);\n      requireAppForgeBiometric(webView);\n');
}

fs.writeFileSync(file, src);
console.log(`[AppForge] security runtime: biometric=${biometric}, secureWindow=${secure}, keepAwake=${keepAwake}`);
