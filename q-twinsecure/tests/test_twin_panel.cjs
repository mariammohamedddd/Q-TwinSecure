// Minimal DOM harness verifies real panel text and safe rendering without dependencies.
const {test} = require('node:test');
const assert = require('node:assert/strict');
require('../web/twin-panel.js');
class Element {
  constructor() { this.children = []; this.style = {setProperty(key, value) { this[key] = value; }}; this.attributes = {}; this.textContent = ''; this.ownerDocument = {createElement: () => new Element()}; }
  setAttribute(key, value) { this.attributes[key] = value; }
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
  assert.match(text(root), /05 Nov 2026/);
  assert.doesNotMatch(text(root), /2026-11-05T12:30:00Z/);
  assert.match(text(root), /sensor location for visual demonstration only/);
  assert.match(text(root), /Illustrative 3D model/);
  assert.match(text(root), /<img src=x/); // textContent, never HTML interpretation
  panel.update({...status,age_seconds:6,freshness:'DELAYED'}); assert.match(text(root), /6.0 seconds/); assert.match(text(root), /DELAYED/);
  panel.update({...status,age_seconds:16,freshness:'MISSING'}); assert.match(text(root), /650 ppm/);
  panel.disconnected(); assert.match(text(root), /Disconnected/); assert.doesNotMatch(text(root), /650 ppm/);
});
test('immersive camera supports zoom limits, rotation and reset', () => {
  const root = new Element(); mountTwinPanel(root, {fullScreen:true});
  const nodes = [];
  function visit(node) { nodes.push(node); node.children.forEach(visit); } visit(root);
  assert.ok(nodes.some(node => node.attributes.class === 'twin-card twin-immersive'));
  const scene = nodes.find(node => node.attributes.class === 'twin-scene');
  const click = label => nodes.find(node => node.textContent === label).onclick();
  for (let n=0;n<40;n++) click('+ Zoom in');
  assert.equal(scene.style['--zoom'], '3');
  for (let n=0;n<40;n++) click('− Zoom out');
  assert.equal(scene.style['--zoom'], '0.5');
  click('Rotate right'); assert.equal(scene.style['--rotation'], '10deg');
  click('Reset view'); assert.equal(scene.style['--zoom'], '1');
  assert.equal(scene.style['--rotation'], '-35deg');
});

test('panel displays real runner snapshots and retains accepted value after tampering', () => {
  const {execFileSync} = require('node:child_process');
  const snapshots = JSON.parse(execFileSync('python', ['-c', `
import base64, json
from unittest.mock import patch
from main import RunnerState, ActionError
from gateway.crypto import encrypt_reading
s = RunnerState(auto_generate=False)
try:
    s.apply({'action':'generate_keys','count':1})
    s.apply({'action':'start_epoch'})
    s.apply({'action':'send_reading'})
    accepted = s.status()['twin']
    def tamper(reading,key):
        envelope = encrypt_reading(reading,key)
        data = bytearray(base64.b64decode(envelope['ciphertext']))
        data[0] ^= 1
        envelope['ciphertext'] = base64.b64encode(data).decode()
        return envelope
    with patch('digital_twin.integration.encrypt_reading',side_effect=tamper):
        try: s.apply({'action':'send_reading'})
        except ActionError: pass
    rejected = s.status()['twin']
    delayed = s.apply({'action':'advance_time','seconds':6})['twin']
    missing = s.apply({'action':'advance_time','seconds':10})['twin']
    reset = s.apply({'action':'reset'})['twin']
    print(json.dumps([accepted,rejected,delayed,missing,reset]))
finally: s.close()
`], {cwd:require('node:path').resolve(__dirname,'..'),encoding:'utf8'}));
  const root = new Element(); const panel = mountTwinPanel(root);
  panel.update(snapshots[0]); const acceptedText = text(root);
  assert.ok(acceptedText.includes(`${snapshots[0].value_ppm} ppm`));
  panel.update(snapshots[1]); assert.equal(text(root), acceptedText);
  panel.update(snapshots[2]); assert.match(text(root), /DELAYED/);
  panel.update(snapshots[3]); assert.match(text(root), /MISSING/); assert.ok(text(root).includes(`${snapshots[0].value_ppm} ppm`));
  panel.update(snapshots[4]); assert.match(text(root), /no accepted observation/); assert.ok(!text(root).includes(`${snapshots[0].value_ppm} ppm`));
});
