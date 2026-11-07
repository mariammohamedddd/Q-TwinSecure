// Check actual shared app render/disconnect paths against real RunnerState snapshots.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { panel } from './test_sensor_panel.mjs';

const snapshots = JSON.parse(execFileSync(process.env.PYTHON || 'python', ['-B', '-c',
  'import json; from main import RunnerState; s=RunnerState(); a=s.status(); b=s.apply({"action":"advance_time","seconds":5}); c=s.apply({"action":"reset"}); print(json.dumps([a,b,c]))'
], { encoding: 'utf8' }));

class Element {
  constructor() { this.children = []; this.textContent = ''; this.dataset = {}; }
  replaceChildren() { this.children = []; }
  append(...children) { this.children.push(...children); }
}
const nodes = new Map();
globalThis.document = {
  body: {dataset:{}},
  querySelector(selector) {
    if (selector === 'co2-sensor-panel') return panel;
    if (!nodes.has(selector)) nodes.set(selector, new Element());
    return nodes.get(selector);
  },
  querySelectorAll() { return []; },
  createElement() { return new Element(); },
};
globalThis.mountTwinPanel = () => ({update(){},disconnected(){}});
const gateway = await readFile(new URL('../web/gateway-panel.js', import.meta.url), 'utf8');
let source = await readFile(new URL('../web/app.js', import.meta.url), 'utf8');
source = source.replace("'./gateway-panel.js'", `'data:text/javascript;base64,${Buffer.from(gateway).toString('base64')}'`)
  .replace("import './sensor-panel.js';", '')
  .replace(/refresh\(\);\s*setInterval\(refresh, 2000\);/, 'export { render, disconnected };');
const { render, disconnected } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
render(snapshots[0]);
assert.equal(panel.field('connection').textContent, 'Awaiting reading');
render(snapshots[1]);
assert.equal(panel.field('id').textContent, snapshots[1].sensor.sensor_id);
assert.equal(panel.field('time').dateTime, snapshots[1].sensor.timestamp);
assert.equal(panel.history.at(-1).value_ppm, snapshots[1].sensor.value_ppm);
assert.match(nodes.get('#scenario-status').textContent, /1 sensor readings generated/);
disconnected();
assert.equal(panel.field('connection').dataset.state, 'offline');
render(snapshots[1]);
assert.equal(panel.field('connection').dataset.state, 'live');
assert.equal(panel.history.length, 1);
render(snapshots[2]);
assert.equal(panel.history.length, 0);
assert.equal(panel.field('time').textContent, '—');
console.log('PASS shared app renders real RunnerState snapshots, disconnects, recovers and resets');
