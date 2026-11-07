// Optional real-browser check using local Chrome DevTools; no npm dependencies.
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';

const app = process.env.REVIEW_APP || 'http://127.0.0.1:18945';
const debug = process.env.REVIEW_BROWSER || 'http://127.0.0.1:18946';
const offline = process.argv.includes('--expect-offline');
const reconnected = process.argv.includes('--expect-reconnected');
assert.match(app, /^http:\/\/127\.0\.0\.1:\d+$/);
assert.match(debug, /^http:\/\/127\.0\.0\.1:\d+$/);
const target = offline || reconnected
  ? (await (await fetch(`${debug}/json/list`)).json()).find(page => page.url.startsWith(app))
  : await (await fetch(`${debug}/json/new?${app}`, {method:'PUT'})).json();
assert.ok(target?.webSocketDebuggerUrl, 'No local browser page available');
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve,reject) => { socket.onopen=resolve; socket.onerror=reject; });
let nextId=0;
const pending=new Map();
const exceptions=[];
socket.onmessage=({data}) => {
  const message=JSON.parse(data);
  if(message.method==='Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text);
  const callback=pending.get(message.id);
  if(!callback) return;
  pending.delete(message.id);
  message.error ? callback.reject(new Error(message.error.message)) : callback.resolve(message.result);
};
function rpc(method,params={}) {
  return new Promise((resolve,reject) => {
    const id=++nextId;
    pending.set(id,{resolve,reject});
    socket.send(JSON.stringify({id,method,params}));
  });
}
async function evaluate(fn,...args) {
  const result=await rpc('Runtime.evaluate',{
    expression:`(${fn.toString()})(...${JSON.stringify(args)})`,returnByValue:true,awaitPromise:true
  });
  if(result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result?.value;
}
async function wait(fn,...args) {
  const deadline=Date.now()+6000;
  while(Date.now()<deadline) {
    if(await evaluate(fn,...args)) return;
    await new Promise(resolve => setTimeout(resolve,40));
  }
  throw new Error(`Browser condition timed out: ${fn.toString()}`);
}
async function click(selector) {
  await wait(selector => {
    const element=document.querySelector(selector);
    return element && !element.matches(':disabled') && getComputedStyle(element).display!=='none';
  },selector);
  await evaluate(selector => document.querySelector(selector).click(),selector);
}
async function action(name) {
  await click(`[data-action="${name}"]`);
  await wait(() => !document.querySelector('#controls').disabled);
}
async function state() { return (await fetch(`${app}/api/status`)).json(); }
async function check(label,fn) { await fn(); console.log(`PASS ${label}`); }
async function navigate(path) {
  await rpc('Page.navigate',{url:`${app}${path}`});
  await wait(() => document.querySelector('#connection')?.dataset.state==='connected');
}
try {
  await rpc('Runtime.enable');
  await rpc('Page.enable');
  if(reconnected) {
    await wait(() => document.querySelector('#connection')?.dataset.state==='connected');
    assert.equal(await evaluate(() => document.querySelector('#controls').disabled),false);
    const status=await state();
    assert.equal(status.clock.mode,'manual');
    assert.equal(status.key_pool.keys_generated,0);
    assert.equal(status.readings_delivered,0);
    assert.equal(status.twin.timestamp,null);
    console.log('PASS browser automatically reconnects after restart with clean manual state');
  } else if(offline) {
    await wait(() => document.querySelector('#connection')?.dataset.state==='disconnected');
    assert.equal(await evaluate(() => document.querySelector('#controls').disabled),true);
    assert.equal(await evaluate(() => document.querySelector('#metric-delivered')?.textContent || '—'),'—');
    console.log('PASS browser detects stopped server and disables controls');
  } else {
    await wait(() => document.querySelector('#connection')?.dataset.state==='connected');
    await check('manual mode shows manual controls and hides automatic/presentation controls',async () => {
      assert.equal((await state()).clock.mode,'manual');
      assert.equal(await evaluate(() => document.body.dataset.mode),'manual');
      assert.equal(await evaluate(() => document.querySelector('#presentation-banner').hidden),true);
      assert.equal(await evaluate(() => getComputedStyle(document.querySelector('[data-action="start_monitoring"]')).display),'none');
    });
    await check('focused navigation opens distinct controls and activity views',async () => {
      await click('.sidebar a[href="#experiment"]');
      await wait(() => document.body.dataset.view==='controls');
      assert.equal(await evaluate(() => getComputedStyle(document.querySelector('.events-surface')).display),'none');
      await click('.sidebar a[href="#activity"]');
      await wait(() => document.body.dataset.view==='activity');
      assert.equal(await evaluate(() => getComputedStyle(document.querySelector('.controls-surface')).display),'none');
      await click('.sidebar a[href="#experiment"]');
      await wait(() => document.body.dataset.view==='controls');
    });
    await check('reset, empty-pool failure and invalid numeric input are visible and safe',async () => {
      await action('reset');
      assert.equal((await state()).readings_delivered,0);
      await action('start_epoch');
      assert.match(await evaluate(() => document.querySelector('#action-error').textContent),/No key available/);
      await evaluate(() => { document.querySelector('#key-count').value='0'; });
      await action('generate_keys');
      assert.equal((await state()).key_pool.keys_generated,0);
      await evaluate(() => { document.querySelector('#key-count').value='1'; });
    });
    let epoch;
    await check('normal UI delivery updates real sensor, gateway, Twin and counters',async () => {
      await action('generate_keys');
      await action('start_epoch');
      epoch=(await state()).gateway.connection_epoch;
      await action('send_reading');
      let status=await state();
      assert.equal(status.sensor.value_ppm,650);
      assert.equal(status.twin.value_ppm,650);
      assert.equal(await evaluate(() => document.querySelector('co2-sensor-panel').field('value').textContent),'650');
      assert.match(await evaluate(() => document.querySelector('#twin-panel').textContent),/650 ppm/);
      await action('send_reading');
      status=await state();
      assert.equal(status.readings_delivered,2);
      assert.equal(status.twin.value_ppm,700);
      assert.equal(status.key_pool.keys_consumed,1);
      assert.equal(status.gateway.connection_epoch,epoch);
      assert.equal(await evaluate(() => document.querySelector('#metric-delivered').textContent),'2');
    });
    await check('interruption preserves active epoch; empty renewal fails; freshness follows manual time',async () => {
      await action('interrupt_supply');
      await action('send_reading');
      assert.equal((await state()).readings_delivered,3);
      assert.equal((await state()).gateway.connection_epoch,epoch);
      await action('generate_keys');
      assert.match(await evaluate(() => document.querySelector('#action-error').textContent),/supply interrupted/);
      await action('end_epoch');
      await action('start_epoch');
      assert.match(await evaluate(() => document.querySelector('#action-error').textContent),/No key available/);
      assert.equal(await evaluate(() => document.querySelector('[data-action="send_reading"]').matches(':disabled')),true);
      await evaluate(() => { document.querySelector('#time-step').value='6'; });
      await action('advance_time');
      assert.equal((await state()).twin.freshness,'DELAYED');
      assert.equal(await evaluate(() => document.querySelector('#metric-freshness').textContent),'DELAYED');
      await evaluate(() => { document.querySelector('#time-step').value='10'; });
      await action('advance_time');
      assert.equal((await state()).twin.freshness,'MISSING');
      assert.equal((await state()).twin.value_ppm,680);
      assert.equal((await state()).readings_delivered,3);
    });
    await check('recovery restores CURRENT with a new epoch and fourth delivery',async () => {
      await action('resume_supply');
      await action('generate_keys');
      await action('start_epoch');
      await action('send_reading');
      const status=await state();
      assert.equal(status.twin.freshness,'CURRENT');
      assert.equal(status.readings_delivered,4);
      assert.equal(status.key_pool.keys_consumed,2);
      assert.notEqual(status.gateway.connection_epoch,epoch);
    });
    await check('factory view shares state and its controls reset the entire demonstration',async () => {
      await navigate('/twin');
      assert.equal((await state()).readings_delivered,4);
      assert.match(await evaluate(() => document.querySelector('#twin-panel').textContent),/650 ppm/);
      assert.equal(await evaluate(() => document.querySelector('.factory-nav').children.length),4);
      await evaluate(() => { document.querySelector('.twin-reading-details>details').open=true; });
      await action('reset');
      const status=await state();
      assert.equal(status.gateway.connection_state,'DISCONNECTED');
      assert.equal(status.key_pool.keys_generated,0);
      assert.equal(status.readings_generated,0);
      assert.equal(status.readings_delivered,0);
      assert.equal(status.twin.freshness,'MISSING');
      assert.equal(status.sensor,null);
    });
    await check('390px dashboard layout fits its viewport and manual controls remain usable',async () => {
      await rpc('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
      await navigate('/#experiment');
      await wait(() => document.body.dataset.view==='controls');
      assert.equal(await evaluate(() => document.documentElement.scrollWidth<=window.innerWidth),true);
      await action('generate_keys');
      assert.equal((await state()).key_pool.keys_generated,1);
    });
    assert.deepEqual(exceptions,[],'Unexpected browser JavaScript exceptions');
    const screenshot=await rpc('Page.captureScreenshot',{format:'png'});
    await writeFile(new URL('../evidence/manual-browser-mobile.png',import.meta.url),Buffer.from(screenshot.data,'base64'));
    console.log('PASS no browser JavaScript exceptions; screenshot saved');
  }
} finally { socket.close(); }
