import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient, featurePlan, capacitorConfigObject, tsConfigSource } from './lib.mjs';

const file = path.resolve(rootDir, process.argv[2] || 'clients/demo.json');
const client = validateClient(readJSON(file));
const plan = featurePlan(client);

fs.writeFileSync(path.join(rootDir, 'capacitor.config.ts'), tsConfigSource(capacitorConfigObject(client)));
fs.writeFileSync(path.join(rootDir, 'generated-client.json'), JSON.stringify(client, null, 2) + '\n');
fs.writeFileSync(path.join(rootDir, 'generated-feature-plan.json'), JSON.stringify(plan, null, 2) + '\n');

console.log(`[AppForge] ${client.appName} -> ${client.mode}${client.url ? ' ' + client.url : ''}`);
console.log('[AppForge] feature plan ->', JSON.stringify(plan));
