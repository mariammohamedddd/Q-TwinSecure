// Exercise the shared polling/wiring code with a real runner status snapshot.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');

test('shared app forwards real Twin status, counters and disconnects to the panel', async () => {
  const snapshot = JSON.parse(execFileSync(process.env.PYTHON || 'python', ['-c', `
import json
from main import RunnerState
s=RunnerState(auto_generate=False)
try:
 s.apply({'action':'generate_keys','count':1})
 s.apply({'action':'start_epoch'})
 s.apply({'action':'send_reading'})
 print(json.dumps(s.status()))
finally:s.close()
`], {cwd:path.resolve(__dirname,'..'),encoding:'utf8'}));
  const elements = new Map();
  const element = () => ({textContent:'',dataset:{},hidden:false,disabled:false,
    replaceChildren(){},append(){}});
  const document = {body:{dataset:{}},querySelector(selector){
    if (selector === 'co2-sensor-panel') return {update(){},unavailable(){}};
    if (!elements.has(selector)) elements.set(selector,element());
    return elements.get(selector);
  },querySelectorAll(){return [];},createElement:element};
  const calls=[]; let disconnected=0; let poll; let offline=false;
  const context={document,renderGatewayPanel(){},renderKeyPanel(){},
    mountTwinPanel(){return {update(status){calls.push(status);},disconnected(){disconnected++;}};},
    AbortController,setTimeout,clearTimeout,
    setInterval(fn){poll=fn;},
    async fetch(){if(offline) throw new Error('offline');return {ok:true,json:async()=>snapshot};}};
  const source=fs.readFileSync(path.resolve(__dirname,'../web/app.js'),'utf8')
    .replace(/^import .*;\r?$/gm,'');
  vm.runInNewContext(source,context);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls.length,1);
  assert.deepEqual(calls[0],snapshot.twin);
  assert.match(elements.get('#scenario-status').textContent,/Delivered: 1/);
  assert.equal(calls[0].value_ppm,snapshot.sensor.value_ppm);
  assert.equal(elements.get('#metric-delivered').textContent, '1');
  assert.equal(elements.get('#metric-freshness').textContent, 'CURRENT');
  assert.equal(elements.get('#metric-connection').textContent, 'Connected');
  offline=true; await poll();
  assert.equal(disconnected,1);
  assert.equal(elements.get('#metric-delivered').textContent, '—');
  assert.equal(elements.get('#controls').disabled,true);
  // Reconnection also updates the operating mode and real-time labels.
  snapshot.monitoring = { mode: 'automatic', running: true,
    reading_interval_seconds: 2, epoch_duration_seconds: 10,
    epoch_remaining_seconds: 8.5, error: null };
  snapshot.clock.mode = 'realtime';
  snapshot.clock.elapsed_seconds = 1.5;
  snapshot.key_supply_mode = 'automatic';
  offline = false;
  await poll();
  assert.equal(document.body.dataset.mode, 'automatic');
  assert.match(elements.get('#clock-status').textContent, /Live clock: 1.5 seconds/);
  assert.match(elements.get('#monitoring-status').textContent, /Automatic monitoring active/);
  assert.match(elements.get('#action-help').textContent, /run automatically/);
});
