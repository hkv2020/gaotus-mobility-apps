import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
export const rootDir=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export const readJSON=f=>JSON.parse(fs.readFileSync(f,'utf8'));
export function validateClient(c){const e=[];if(!c||typeof c!=='object')e.push('config object required');if(!/^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*){2,}$/.test(c?.appId||''))e.push('invalid appId');if(!String(c?.appName||'').trim())e.push('appName required');if(!['local','remote'].includes(c?.mode))e.push('mode must be local or remote');if(c?.mode==='remote'){try{const u=new URL(c.url);if(!['http:','https:'].includes(u.protocol))e.push('remote url must use http/https')}catch{e.push('valid remote url required')}}if(!/^#[0-9a-fA-F]{6}$/.test(c?.themeColor||''))e.push('themeColor must be #RRGGBB');if(!Number.isInteger(c?.versionCode)||c.versionCode<1)e.push('versionCode >= 1 required');if(!/^\d+\.\d+\.\d+/.test(c?.versionName||''))e.push('versionName required');if(e.length)throw new Error(e.join('\n'));return c}
export function capacitorConfigObject(c){const x={appId:c.appId,appName:c.appName,webDir:'www',backgroundColor:c.themeColor,server:{errorPath:'offline.html'}};if(c.mode==='remote'){const u=new URL(c.url);x.server.url=c.url;x.server.allowNavigation=[u.hostname,`*.${u.hostname}`];if(u.protocol==='http:')x.server.cleartext=true}return x}
export const tsConfigSource=c=>`import type { CapacitorConfig } from '@capacitor/cli';\nconst config: CapacitorConfig = ${JSON.stringify(c,null,2)};\nexport default config;\n`;
