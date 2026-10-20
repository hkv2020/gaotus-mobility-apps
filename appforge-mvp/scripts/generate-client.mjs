import fs from 'node:fs';
import path from 'node:path';
import { rootDir, readJSON, validateClient, resolveEnvironmentTokens, featurePlan, capacitorConfigObject, tsConfigSource } from './lib.mjs';
import { normalizeBuilderInput } from './normalize-builder-input.mjs';

const file = path.resolve(rootDir, process.argv[2] || 'clients/demo.json');
const input = normalizeBuilderInput(readJSON(file));
const raw = validateClient(input);
const client = resolveEnvironmentTokens(raw);
validateClient({ ...client, environment: (client.environment || []).filter((row) => row.key !== 'BASE_URL') });
const plan = featurePlan(client);

fs.writeFileSync(path.join(rootDir, 'capacitor.config.ts'), tsConfigSource(capacitorConfigObject(client)));
fs.writeFileSync(path.join(rootDir, 'generated-client.json'), JSON.stringify(client, null, 2) + '\n');
fs.writeFileSync(path.join(rootDir, 'generated-feature-plan.json'), JSON.stringify(plan, null, 2) + '\n');

console.log(`[AppForge] ${client.appName} -> ${client.mode}${client.url ? ' ' + client.url : ''}`);
console.log('[AppForge] environment ->', JSON.stringify(Object.fromEntries((client.environment || []).map((row) => [row.key, row.value]))));
console.log('[AppForge] feature plan ->', JSON.stringify(plan));
