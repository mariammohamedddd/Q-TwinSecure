// Exercise the shared polling/wiring code with a real runner status snapshot.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');

test('shared app forwards real Twin status, counters and disconnects to the panel', async () => {
  const snapshot = JSON.parse(execFileSync('python', ['-c', `
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
    if (!elements.has(selector)) elements.set(selector,element());
    return elements.get(selector);
  },querySelectorAll(){return [];},createElement:element};
  const calls=[]; let disconnected=0; let poll; let offline=false;
  const context={document,renderGatewayPanel(){},
    mountTwinPanel(){return {update(status){calls.push(status);},disconnected(){disconnected++;}};},
    AbortController,setTimeout,clearTimeout,
    setInterval(fn){poll=fn;},
    async fetch(){if(offline) throw new Error('offline');return {ok:true,json:async()=>snapshot};}};
  const source=fs.readFileSync(path.resolve(__dirname,'../web/app.js'),'utf8')
    .replace("import { renderGatewayPanel } from './gateway-panel.js';",'');
  vm.runInNewContext(source,context);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls.length,1);
  assert.deepEqual(calls[0],snapshot.twin);
  assert.match(elements.get('#scenario-status').textContent,/1 delivered/);
  assert.match(elements.get('#sensor-panel').textContent,/650 ppm/);
  offline=true; await poll();
  assert.equal(disconnected,1);
  assert.equal(elements.get('#controls').disabled,true);
});
