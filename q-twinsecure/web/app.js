import { renderKeyPanel } from './key-panel.js';
import './sensor-panel.js';
import './twin-panel.js';
const twinPanel = globalThis.mountTwinPanel(document.querySelector('#twin-panel'), {
  fullScreen: document.body.dataset.layout === 'immersive'
});
if (document.body.dataset.layout === 'immersive') {
  const detailPanel = document.querySelector('.twin-reading-details');
  const disclosure = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = 'Experiment controls';
  disclosure.append(summary, document.querySelector('[aria-labelledby="controls-title"]'));
  detailPanel.prepend(disclosure);
}
const sensorPanel = document.querySelector('co2-sensor-panel');
import { renderGatewayPanel } from "./gateway-panel.js";
const connection = document.querySelector('#connection');
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
    button.disabled = busy || !online || !capability?.enabled;
    button.title = capability?.reason || '';
  }
  document.querySelector('#key-count').disabled = !latestStatus?.actions?.generate_keys?.enabled;
  document.querySelector('#time-step').disabled = !latestStatus?.actions?.advance_time?.enabled;
}

function updateOverview(status) {
  // The immersive page shares this app but does not contain overview cards.
  const set = (selector, value, state) => {
    const node = document.querySelector(selector);
    if (!node) return;
    node.textContent = value;
    if (state) node.dataset.state = state;
    else delete node.dataset.state;
  };
  if (!status) {
    for (const id of ['keys', 'connection', 'delivered', 'freshness']) set(`#metric-${id}`, '—');
    for (const id of ['key-note', 'epoch', 'delivery-note', 'age']) set(`#metric-${id}`, 'Live status unavailable');
    return;
  }
  set('#metric-keys', String(status.key_pool.keys_available));
  set('#metric-key-note', `${status.key_pool.keys_consumed} pairs allocated · ${status.key_pool.supply_enabled ? 'Supply enabled' : 'Supply interrupted'}`);
  const connected = status.gateway.connection_state === 'CONNECTED';
  set('#metric-connection', connected ? 'Connected' : 'Disconnected');
  set('#metric-epoch', connected ? `Epoch ${status.gateway.connection_epoch.slice(0, 8)}…` : 'Ready for a new epoch');
  set('#metric-delivered', String(status.readings_delivered));
  set('#metric-delivery-note', `${status.readings_generated} generated · ${status.readings_rejected} rejected`);
  set('#metric-freshness', status.twin.freshness, status.twin.freshness);
  set('#metric-age', status.twin.age_seconds == null ? 'No accepted observation yet' : `Observation age · ${status.twin.age_seconds.toFixed(1)} seconds`);
}

function renderPresentation(presentation) {
  document.body.dataset.presentation = presentation ? 'on' : 'off';
  const banner = document.querySelector('#presentation-banner');
  if (!banner) return;
  banner.hidden = !presentation;
  if (!presentation) return;
  document.querySelector('#presentation-progress').textContent = `GUIDED PRESENTATION · STEP ${presentation.step} / ${presentation.total_steps}`;
  document.querySelector('#presentation-title').textContent = presentation.error ? 'Scenario check failed' : presentation.title;
  document.querySelector('#presentation-description').textContent = presentation.error || presentation.description;
  const bar = document.querySelector('#presentation-progress-bar');
  bar.max = presentation.total_steps;
  bar.value = presentation.step;
  const steps = document.querySelector('#presentation-steps');
  steps.replaceChildren();
  presentation.steps.forEach((step, index) => {
    const item = document.createElement('li');
    item.dataset.state = step.state;
    item.textContent = `${index + 1}. ${step.title}`;
    steps.append(item);
  });
  const results = document.querySelector('#presentation-results');
  results.replaceChildren();
  for (const result of presentation.results) {
    const item = document.createElement('li');
    item.textContent = `${result.passed ? '✓' : '✕'} ${result.label}`;
    results.append(item);
  }
}

function render(status) {
  if (status.api_version !== 1 || status.phase !== 3 || !status.actions || !status.clock || !Array.isArray(status.events)) {
    throw new Error('Unsupported runner contract');
  }
  renderGatewayPanel(document.querySelector("#gateway-panel"), status.gateway);
  renderKeyPanel(document.querySelector('#key-panel'), status.key_pool, { mode: status.presentation ? 'presentation' : status.key_supply_mode });
  sensorPanel.update(status.sensor);
  twinPanel.update(status.twin);
  document.querySelector('#scenario-status').textContent = `Scenario: ${status.scenario} · Generated: ${status.readings_generated} · Delivered: ${status.readings_delivered} · Rejected: ${status.readings_rejected}`;
  document.body.dataset.mode = status.monitoring?.mode || 'manual';
  const monitoringStatus = document.querySelector('#monitoring-status');
  if (monitoringStatus) {
    const monitoring = status.monitoring;
    monitoringStatus.textContent = status.presentation
      ? 'Guided scenario demonstration · real-time observations · Replay restarts from a clean state'
      : monitoring?.mode === 'automatic'
      ? (monitoring.error || `${monitoring.running ? 'Automatic monitoring active' : 'Monitoring stopped'} · Readings every ${monitoring.reading_interval_seconds}s · Epoch lifetime ${monitoring.epoch_duration_seconds}s${monitoring.epoch_remaining_seconds == null ? ' · Waiting for connection' : ` · Renewal in ${monitoring.epoch_remaining_seconds.toFixed(1)}s`}`)
      : 'Manual demonstration · use the controls to generate, send and advance time.';
  }
  renderPresentation(status.presentation);
  updateOverview(status);
  latestStatus = status;
  online = true;
  connection.textContent = document.body.dataset.layout === 'immersive' ? 'Runner connected' : 'Local runner connected · Integrated components';
  connection.dataset.state = 'connected';
  document.querySelector('#clock-status').textContent = status.clock.mode === 'realtime'
    ? `Live clock: ${status.clock.elapsed_seconds.toFixed(1)} seconds elapsed · freshness updates automatically`
    : `Experiment clock: ${status.clock.elapsed_seconds} seconds (manual; paused between actions)`;
  document.querySelector('#action-help').textContent = status.presentation
    ? 'The presentation controls the real components. Watch each checkpoint above; use Replay to run all scenarios again. Individual controls are disabled to preserve the demonstration.'
    : status.clock.mode === 'realtime'
    ? 'Keys, sensor sampling, delivery and epoch renewal run automatically. Supply interruption preserves the active epoch and buffered keys. After keys run out, freshness ages until supply recovers. Stop monitoring pauses readings; real time continues.'
    : `Observation time is manual; keys are ${status.key_supply_mode}. Generate keys, start an epoch, then send readings. Clock limit: 86400 seconds.`;
  const events = document.querySelector('#events');
  events.replaceChildren();
  document.querySelector('#event-empty').hidden = status.events.length > 0;
  for (const event of [...status.events].reverse()) {
    const item = document.createElement('li');
    item.dataset.outcome = event.outcome;
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
  renderPresentation(null);
  updateOverview(null);
  renderKeyPanel(document.querySelector('#key-panel'), null, { state: 'disconnected' });
  sensorPanel.unavailable();
  twinPanel.disconnected();
  renderGatewayPanel(document.querySelector("#gateway-panel"), null);
  connection.textContent = document.body.dataset.layout === 'immersive' ? 'Runner offline · reconnecting' : 'Disconnected · Local runner unavailable. Check the terminal; retrying automatically. Displayed events may be stale.';
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
setInterval(refresh, 1000);

// Hash links select a focused workspace without duplicating state or polling.
if (typeof window !== 'undefined' && document.body.classList?.contains('dashboard')) {
  const applyNavigation = () => {
    const hash = window.location.hash || '#workspace';
    document.body.dataset.view = ['#experiment', '#controls-title'].includes(hash) ? 'controls'
      : ['#activity', '#events-title'].includes(hash) ? 'activity' : 'overview';
    const breadcrumb = document.querySelector('.breadcrumb strong');
    if (breadcrumb) breadcrumb.textContent = document.body.dataset.view === 'controls' ? 'Experiment controls' : document.body.dataset.view === 'activity' ? 'Activity log' : 'Overview';
    for (const link of document.querySelectorAll('.sidebar nav a[href^="#"]')) {
      const active = link.getAttribute('href') === hash;
      link.classList.toggle('nav-active', active);
      if (active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
    if (document.body.dataset.view !== 'overview') window.scrollTo(0, 0);
  };
  window.addEventListener('hashchange', applyNavigation);
  applyNavigation();
}
