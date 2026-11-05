// Minimal DOM harness verifies real panel text and safe rendering without dependencies.
const {test} = require('node:test');
const assert = require('node:assert/strict');
require('../web/twin-panel.js');
class Element {
  constructor() { this.children = []; this.style = {}; this.textContent = ''; this.ownerDocument = {createElement: () => new Element()}; }
  setAttribute() {}
  append(...items) { this.children.push(...items); }
  replaceChildren() { this.children = []; }
}
function text(node) { return [node.textContent, ...node.children.map(text)].join(' '); }
test('Twin panel handles loading, empty, real status, expiration and disconnect', () => {
  const root = new Element(); const panel = mountTwinPanel(root);
  assert.match(text(root), /Loading/);
  panel.update(null); assert.match(text(root), /no accepted observation/);
  const status = {sensor_id:'<img src=x onerror=alert(1)>',value_ppm:650,timestamp:'2026-11-05T12:30:00Z',received_at:'2026-11-05T12:30:00Z',age_seconds:0,freshness:'CURRENT',current_threshold:5,missing_threshold:15};
  panel.update(status); assert.match(text(root), /650 ppm/); assert.match(text(root), /CURRENT/);
  assert.match(text(root), /<img src=x/); // textContent, never HTML interpretation
  panel.update({...status,age_seconds:6,freshness:'DELAYED'}); assert.match(text(root), /6.0 seconds/); assert.match(text(root), /DELAYED/);
  panel.update({...status,age_seconds:16,freshness:'MISSING'}); assert.match(text(root), /650 ppm/);
  panel.disconnected(); assert.match(text(root), /Disconnected/); assert.doesNotMatch(text(root), /650 ppm/);
});
