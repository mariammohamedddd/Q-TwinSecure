// No dependencies: exercise the component using a minimal DOM adapter.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

let Panel;
globalThis.HTMLElement = class {
  attachShadow() {
    const fields = new Map();
    this.shadowRoot = {
      innerHTML: '',
      querySelector(selector) {
        if (!fields.has(selector)) fields.set(selector, {
          textContent: '', dataset: {}, style: {}, hidden: false,
          attributes: {}, setAttribute(key, value) { this.attributes[key] = value; },
        });
        return fields.get(selector);
      },
    };
  }
};
globalThis.customElements = { define(name, cls) { Panel = cls; } };
// Import as ESM without adding package.json to the Python repository.
const source = await readFile(new URL('../web/sensor-panel.js', import.meta.url), 'utf8');
// Component resolves its stylesheet relative to a file URL in browsers.
const moduleSource = source.replace("new URL('./sensor-panel.css', import.meta.url)", "new URL('file:///sensor-panel.css')");
const { validReading, startSensorPolling } = await import(`data:text/javascript;base64,${Buffer.from(moduleSource).toString('base64')}`);
const reading = { sensor_id: '<b>sensor</b>', value_ppm: 650, timestamp: '2026-11-05T12:30:00+00:00' };
assert.equal(validReading(reading), true);
for (const invalid of [null, {}, { ...reading, value_ppm: NaN }, { ...reading, value_ppm: true },
  { ...reading, sensor_id: ' ' }, { ...reading, timestamp: '2026-11-05T12:30:00' }]) {
  assert.equal(validReading(invalid), false);
}
console.log('PASS reading validation');
const panel = new Panel();
panel.update(null);
assert.equal(panel.field('connection').textContent, 'Awaiting reading');
assert.equal(panel.history.length, 0);
panel.update(reading);
assert.equal(panel.field('id').textContent, '<b>sensor</b>');
assert.equal(panel.field('time').textContent, '12:30:00');
panel.update(reading);
assert.equal(panel.history.length, 1);
console.log('PASS empty, render, text safety and duplicate observations');
for (let i = 0; i < 40; i++) panel.update({ ...reading, value_ppm: 500 + i });
assert.equal(panel.history.length, 30);
panel.unavailable();
assert.equal(panel.field('value').textContent, '—');
assert.equal(panel.history.length, 30);
panel.update(reading);
assert.equal(panel.field('connection').dataset.state, 'live');
panel.update({ ...reading, value_ppm: -1 });
assert.equal(panel.field('connection').dataset.state, 'offline');
panel.update(null);
assert.equal(panel.history.length, 0);
console.log('PASS bounded chart, disconnect, recovery, invalid state and reset');
const flush = () => new Promise(resolve => setTimeout(resolve, 5));
globalThis.fetch = async () => ({ ok: true, json: async () => ({ sensor: reading }) });
let stop = startSensorPolling(panel, { interval: 10000 });
await flush(); stop();
assert.equal(panel.field('connection').dataset.state, 'live');
globalThis.fetch = async () => { throw new Error('offline'); };
stop = startSensorPolling(panel, { interval: 10000 });
await flush(); stop();
assert.equal(panel.field('connection').dataset.state, 'offline');
console.log('PASS polling success, failure and cleanup');

export { panel };
