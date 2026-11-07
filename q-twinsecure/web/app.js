const connection = document.querySelector('#connection');
import { renderGatewayPanel } from './gateway-panel.js';

const twinPanel = globalThis.mountTwinPanel(document.querySelector('#twin-panel'), {
  fullScreen: document.body.dataset.layout === 'immersive',
});
if (document.body.dataset.layout === 'immersive') {
  const detailPanel = document.querySelector('.twin-reading-details');
  const disclosure = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = 'Experiment controls';
  disclosure.append(summary, document.querySelector('[aria-labelledby="controls-title"]'));
  detailPanel.prepend(disclosure);
}
const controls = document.querySelector('#controls');
const actionError = document.querySelector('#action-error');
const buttons = [...document.querySelectorAll('[data-action]')];
let busy = false;
let online = false;
let latestStatus = null;

function setControls() {
  controls.disabled = busy || !online;
  for (const button of buttons) {
    const capability = latestStatus?.actions?.[button.dataset.action];
    button.disabled = !capability?.enabled;
    button.title = capability?.reason || '';
  }
  document.querySelector('#key-count').disabled = !latestStatus?.actions?.generate_keys?.enabled;
}

function render(status) {
  if (status.api_version !== 1 || status.phase !== 3 || !status.actions || !status.clock || !Array.isArray(status.events)) {
    throw new Error('Unsupported runner contract');
  }
  latestStatus = status;
  online = true;
  renderGatewayPanel(document.querySelector('#gateway-panel'), status.gateway);
  twinPanel.update(status.twin);
  const key = status.key_pool;
  document.querySelector('#key-panel').textContent = key ? `Key supply: ${key.supply_enabled ? 'enabled' : 'interrupted'} · ${key.keys_available} available · ${key.keys_generated} generated · ${key.keys_consumed} consumed` : 'Key supply unavailable';
  document.querySelector('#sensor-panel').textContent = status.sensor ? `Sensor ${status.sensor.sensor_id} · ${status.sensor.value_ppm} ppm · ${status.sensor.timestamp}` : 'Sensor: no generated reading yet';
  document.querySelector('#scenario-status').textContent = `Manual experiment · ${status.readings_generated} generated · ${status.readings_delivered} delivered · ${status.readings_rejected} rejected`;
  connection.textContent = 'Local runner connected · Real component state';
  connection.dataset.state = 'connected';
  document.querySelector('#clock-status').textContent = `Experiment clock: ${status.clock.elapsed_seconds} seconds (manual; paused between actions)`;
  document.querySelector('#action-help').textContent = `Freshness uses the paused experiment clock; ${status.key_supply_mode === 'automatic' ? 'keys replenish on wall time' : 'keys are generated manually'}. For interruption: pause supply, consume queued keys, then request a new epoch with the pool empty. Clock limit: 86400 seconds.`;
  const events = document.querySelector('#events');
  events.replaceChildren();
  document.querySelector('#event-empty').hidden = status.events.length > 0;
  for (const event of [...status.events].reverse()) {
    const item = document.createElement('li');
    item.textContent = `${event.timestamp} · +${event.elapsed_seconds}s · ${event.action} · ${event.outcome}: ${event.message}`;
    events.append(item);
  }
  setControls();
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 4000);
  try {
    const response = await fetch(path, { ...options, cache: 'no-store', signal: controller.signal });
    const data = await response.json();
    return { response, data };
  } finally {
    clearTimeout(timeout);
  }
}

function disconnected() {
  online = false;
  twinPanel.disconnected();
  renderGatewayPanel(document.querySelector('#gateway-panel'), null);
  connection.textContent = 'Disconnected · Local runner unavailable. Check the terminal; retrying automatically. Displayed events may be stale.';
  connection.dataset.state = 'disconnected';
  setControls();
}

async function refresh() {
  if (busy) return;
  busy = true;
  setControls();
  try {
    const { response, data } = await request('/api/status');
    if (!response.ok) throw new Error('Runner unavailable');
    render(data);
  } catch {
    disconnected();
  } finally {
    busy = false;
    setControls();
  }
}

async function act(action) {
  if (busy || !online || !latestStatus?.actions?.[action]?.enabled) return;
  const payload = { action };
  actionError.hidden = true;
  if (action === 'advance_time' || action === 'generate_keys') {
    const input = document.querySelector(action === 'advance_time' ? '#time-step' : '#key-count');
    if (!input.reportValidity()) return;
    payload[action === 'advance_time' ? 'seconds' : 'count'] = Number(input.value);
  }
  busy = true;
  setControls();
  try {
    const { response, data } = await request('/api/actions', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    });
    if (!response.ok) {
      if (data.status) render(data.status);
      actionError.textContent = data.error || 'Action failed.';
      actionError.hidden = false;
      return;
    }
    render(data);
  } catch {
    disconnected();
    actionError.textContent = 'Action result unknown. Reconnect and check the clock and events before trying again.';
    actionError.hidden = false;
  } finally {
    busy = false;
    setControls();
  }
}

for (const button of buttons) button.addEventListener('click', () => act(button.dataset.action));
refresh();
setInterval(refresh, 2000);
