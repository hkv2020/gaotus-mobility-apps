# Gaotus AppForge MVP 0.1.0

A master mobile wrapper that can be configured per client and built for Android/iOS without maintaining a separate codebase per customer.

## What is already in this MVP

- One client config (`clients/*.json`) controls app id, app name, version, mode and target URL.
- Local self-test mode with a native bridge test screen.
- Remote website mode via Capacitor `server.url` for the first MVP.
- `window.GaotusNative` JavaScript API.
- Android raw bridge: ping, device info, share sheet, haptics, external URL, camera launch and toast.
- iOS raw bridge: share sheet, haptics, external URL, camera-command proof and toast.
- Browser fallbacks for development.
- Config validation that fails closed before a build.
- CI workflows for an installable Android debug APK, Android AAB and an unsigned iOS Simulator compile.

## Local smoke test (no npm required)

Open `www/index.html` in a browser. Native-only actions use safe browser fallbacks.

Run generator unit tests:

```bash
node --test tests/*.test.mjs
node scripts/generate-client.mjs clients/demo.json
```

## Full native build

```bash
npm install
npm run generate
npx cap add android
npx cap add ios
node scripts/patch-native.mjs all
npx cap sync
```

Android installable debug APK:

```bash
cd android
./gradlew assembleDebug
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk`.

## Create a client app

Copy `clients/demo.json` and change:

```json
{
  "appId": "com.customer.app",
  "appName": "Customer App",
  "mode": "remote",
  "url": "https://customer.example"
}
```

Then run:

```bash
node scripts/generate-client.mjs clients/customer.json
```

The build uses the same master shell; only configuration and assets change.

## Website bridge

The canonical API is exposed as `window.GaotusNative`. For example:

```js
await GaotusNative.share({ title: 'Product', url: location.href });
await GaotusNative.haptic('medium');
await GaotusNative.openExternal('https://gaotus.ai');
const info = await GaotusNative.deviceInfo();
```

For a remote website, the production SaaS will inject/serve the connector automatically. The MVP proves the native contract in bundled self-test mode first.

## Important MVP note

Capacitor documents `server.url`/`allowNavigation` primarily for development/live-loading and says these options are not intended as the final production architecture. AppForge therefore treats remote `server.url` as the fast MVP path only. The production wrapper should move remote URL loading and script injection into the native shell while retaining the same `GaotusNative` contract.
