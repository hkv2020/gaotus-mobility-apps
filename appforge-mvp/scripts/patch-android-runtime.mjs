import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { rootDir } from './lib.mjs';

const steps = [
  ['patch-native.mjs', 'android'],
  ['patch-android-permissions.mjs'],
  ['apply-origin-policy.mjs'],
  ['patch-android-back.mjs'],
  ['patch-android-ui.mjs'],
  ['patch-android-webview.mjs'],
  ['patch-android-notifications.mjs'],
  ['patch-android-security.mjs'],
  ['verify-android-runtime.mjs'],
];

for (const [script, ...args] of steps) {
  const full = path.join(rootDir, 'scripts', script);
  console.log(`[AppForge] runtime step -> ${script}${args.length ? ' ' + args.join(' ') : ''}`);
  const result = spawnSync(process.execPath, [full, ...args], { cwd: rootDir, stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${script} failed with exit code ${result.status}`);
}

console.log('[AppForge] Android runtime patch pipeline completed and verified');
