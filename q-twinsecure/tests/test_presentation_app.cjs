const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');

test('guided banner and verified results use real completed presentation state', () => {
  const status = JSON.parse(execFileSync(process.env.PYTHON || 'python', ['-B','-c', `
import json,time
from main import RunnerState
s=RunnerState(presentation=True,presentation_hold=.06,reading_interval=.02,current_threshold=.12,missing_threshold=.3)
try:
 deadline=time.monotonic()+5
 while not s.status()['presentation']['complete'] and time.monotonic()<deadline:
  if s.status()['presentation']['error']: raise RuntimeError('Presentation failed')
  time.sleep(.01)
 print(json.dumps(s.status()))
finally:s.close()
`],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'}));
  assert.equal(status.presentation.complete,true);
  const nodes = new Map();
  const element = () => ({textContent:'',dataset:{},hidden:false,children:[],disabled:false,
    replaceChildren(){this.children=[];},append(...children){this.children.push(...children);}});
  const sensor = {update(){},unavailable(){}};
  const document = {body:{dataset:{}},querySelector(selector){
    if(selector==='co2-sensor-panel')return sensor;
    if(!nodes.has(selector))nodes.set(selector,element());
    return nodes.get(selector);
  },querySelectorAll(){return [];},createElement:element};
  const context={document,renderKeyPanel(){},renderGatewayPanel(){},
    mountTwinPanel(){return {update(){},disconnected(){}};},AbortController,setTimeout,clearTimeout};
  const source=fs.readFileSync(path.resolve(__dirname,'../web/app.js'),'utf8')
    .replace(/^import .*;\r?$/gm,'')
    .replace(/refresh\(\);\s*setInterval\(refresh, 1000\);/,'');
  vm.runInNewContext(source,context);
  context.render(status);
  assert.equal(document.body.dataset.presentation,'on');
  assert.equal(nodes.get('#presentation-banner').hidden,false);
  assert.equal(nodes.get('#presentation-title').textContent,'Demonstration complete');
  assert.match(nodes.get('#presentation-progress').textContent,/STEP 9 \/ 9/);
  assert.equal(nodes.get('#presentation-steps').children.length,9);
  assert.ok(nodes.get('#presentation-results').children.length>=9);
  assert.match(nodes.get('#action-help').textContent,/Replay/);
  assert.match(nodes.get('#monitoring-status').textContent,/Guided scenario/);
  context.disconnected();
  assert.equal(nodes.get('#presentation-banner').hidden,true);
  assert.equal(document.body.dataset.presentation,'off');
});
