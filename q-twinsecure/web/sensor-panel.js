/* Reusable sensor element. Nancy can call panel.update(status.sensor) directly. */
export function validReading(reading) {
  return reading !== null && typeof reading === 'object' &&
    typeof reading.sensor_id === 'string' && reading.sensor_id.trim().length > 0 &&
    typeof reading.value_ppm === 'number' && Number.isFinite(reading.value_ppm) && reading.value_ppm >= 0 &&
    typeof reading.timestamp === 'string' &&
    /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(reading.timestamp) && Number.isFinite(Date.parse(reading.timestamp));
}

class SensorPanel extends HTMLElement {
  constructor() {
    super();
    this.history = [];
    this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="${new URL('./sensor-panel.css', import.meta.url)}">
      <section class="sensor-panel" aria-label="CO2 sensor observatory">
        <div class="ambient" aria-hidden="true">
          <svg class="sensor-art" viewBox="0 0 900 650" fill="none">
            <defs><pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="currentColor"/></pattern></defs>
            <rect width="900" height="650" fill="url(#dots)" opacity=".3"/>
            <g stroke="currentColor" stroke-width="1.2"><path d="M420 120h110v100h150v170H530v150H360V380H200V220h220z" stroke-dasharray="5 9"/>
              <circle cx="530" cy="320" r="160" opacity=".25"/><circle cx="530" cy="320" r="200" opacity=".15"/>
              <g transform="translate(440 200) rotate(12 90 120)"><rect width="180" height="240" rx="28" fill="#10252c"/><rect x="15" y="15" width="150" height="210" rx="20"/><rect x="36" y="44" width="108" height="70" rx="8" fill="#163b3b"/><path d="M50 150h80m-80 12h80m-80 12h80m-80 12h80"/><circle cx="90" cy="208" r="4" fill="#9cebc8"/><path d="M58 -25q32 -34 64 0m-49 -17q17 -18 34 0"/></g>
              <g transform="translate(720 420) rotate(-16)"><rect width="90" height="120" rx="15" fill="#10252c"/><circle cx="45" cy="42" r="20"/><path d="M23 82h44m-44 9h44m-44 9h44"/></g>
              <g transform="translate(200 100) rotate(-12)"><rect width="70" height="95" rx="12" fill="#10252c"/><circle cx="35" cy="32" r="15"/><path d="M17 64h36m-36 10h36"/></g>
              <circle cx="200" cy="380" r="5"/><circle cx="680" cy="220" r="5"/><path d="M700 100h40m-20 -20v40M310 510h28m-14 -14v28"/>
            </g>
          </svg>
        </div>
        <div class="panel-top"><span class="eyebrow"><span class="tiny-square"></span> OBSERVATION NODE / 01</span><span class="connection" role="status" data-field="connection">Connecting</span></div>
        <div class="intro"><p class="eyebrow muted">SENSOR TELEMETRY</p><h1>A clearer view.<br><span>One reading at a time.</span></h1><p class="intro-copy">Explore your simulated environment through<br class="desktop-break"> timestamped carbon dioxide observations.</p></div>
        <div class="workspace">
          <article class="reading-card"><div class="card-heading"><span class="eyebrow">CARBON DIOXIDE</span><span class="chemical">CO₂</span></div>
            <div class="value-row"><span class="reading-value" data-field="value">—</span><span class="unit">ppm</span></div>
            <p class="reading-caption" data-field="caption">Waiting for the first observation</p>
            <div class="range-track" aria-hidden="true"><span data-field="marker"></span></div>
            <div class="range-labels"><span>400 ppm</span><span>SIMULATION RANGE</span><span>1,000 ppm</span></div>
            <div class="reading-meta"><div><span class="meta-label">SENSOR ID</span><strong data-field="id">—</strong></div><span class="node-icon" aria-hidden="true">⌁</span></div>
            <div class="timestamp"><span class="meta-label">OBSERVED AT · UTC</span><time data-field="time">—</time><span class="timestamp-date" data-field="date">No observation yet</span></div>
          </article>
          <article class="history-card"><div class="history-heading"><div><p class="eyebrow muted">THE SIGNAL OVER TIME</p><h2>Recent observations</h2></div><span class="history-limit">LAST 30</span></div>
            <div class="chart-wrap"><div class="chart-labels"><span data-field="chartMax">1,000</span><span>ppm</span><span data-field="chartMin">400</span></div><svg class="chart" viewBox="0 0 600 170" role="img" aria-label="Recent CO2 observations"><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#9cebc8" stop-opacity=".2"/><stop offset="1" stop-color="#9cebc8" stop-opacity="0"/></linearGradient></defs><path class="grid" d="M0 15h600M0 85h600M0 155h600"/><path data-field="area" fill="url(#fill)"/><path data-field="line" fill="none" stroke="#a7efd0" stroke-width="2.5"/><circle data-field="point" r="4" fill="#b8ffdb" visibility="hidden"/></svg><p class="chart-empty" data-field="chartEmpty">Your signal starts with the first reading.</p></div>
            <div class="chart-footer"><span>Earlier</span><span>Latest observation</span></div>
            <div class="stats"><div><span class="meta-label">OBSERVED MIN</span><strong data-field="min">—</strong></div><div><span class="meta-label">OBSERVED MAX</span><strong data-field="max">—</strong></div><div><span class="meta-label">IN THIS VIEW</span><strong data-field="count">0 <small>samples</small></strong></div></div>
            <div class="source-note"><span class="source-icon" aria-hidden="true">◎</span><div><strong>A simulated sensor. Real backend data.</strong><p>Generated by the Python CO₂ simulator.<br>No physical hardware is connected.</p></div></div>
          </article>
        </div>
        <div class="panel-bottom"><span><span class="tiny-square"></span> SOFTWARE SENSOR SIMULATION</span><span>Measured in parts per million</span></div>
      </section>`;
  }

  field(name) { return this.shadowRoot.querySelector(`[data-field="${name}"]`); }
  setState(state, message) {
    this.field('connection').dataset.state = state;
    this.field('connection').textContent = message;
  }
  unavailable(message = 'Disconnected') {
    this.setState('offline', message);
    this.field('value').textContent = '—';
    this.field('caption').textContent = 'Sensor unavailable · waiting to reconnect';
    this.field('marker').hidden = true;
  }
  update(reading) {
    if (reading === null) {
      this.history = [];
      this.setState('empty', 'Awaiting reading');
      for (const key of ['value', 'id', 'time']) this.field(key).textContent = '—';
      this.field('date').textContent = 'No observation yet';
      this.field('caption').textContent = 'Waiting for the first observation';
      this.field('marker').hidden = true;
      this.draw();
      return;
    }
    if (!validReading(reading)) { this.unavailable('Invalid sensor data'); return; }
    this.setState('live', 'Receiving readings');
    this.field('value').textContent = reading.value_ppm.toLocaleString(undefined, { maximumFractionDigits: 1 });
    this.field('caption').textContent = 'Latest generated observation';
    this.field('id').textContent = reading.sensor_id;
    const date = new Date(reading.timestamp);
    this.field('time').textContent = date.toISOString().slice(11, 19);
    this.field('time').dateTime = reading.timestamp;
    this.field('date').textContent = date.toLocaleDateString(undefined, { timeZone: 'UTC', year: 'numeric', month: 'long', day: 'numeric' });
    this.field('marker').hidden = false;
    this.field('marker').style.left = `${Math.max(0, Math.min(100, (reading.value_ppm - 400) / 6))}%`;
    const last = this.history.at(-1);
    if (last && last.sensor_id !== reading.sensor_id) this.history = [];
    if (!last || last.timestamp !== reading.timestamp || last.sensor_id !== reading.sensor_id || last.value_ppm !== reading.value_ppm) {
      this.history.push({ ...reading });
      this.history = this.history.slice(-30);
    }
    this.draw();
  }
  draw() {
    const values = this.history.map(r => r.value_ppm);
    const low = Math.min(400, ...values), high = Math.max(1000, ...values);
    const points = values.map((v, i) => [values.length === 1 ? 590 : 10 + i * 580 / (values.length - 1), 155 - (v - low) / (high - low) * 140]);
    const path = points.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(' ');
    this.field('line').setAttribute('d', path);
    this.field('area').setAttribute('d', points.length > 1 ? `${path} L${points.at(-1)[0]},170 L${points[0][0]},170 Z` : '');
    this.field('point').setAttribute('visibility', points.length ? 'visible' : 'hidden');
    if (points.length) { this.field('point').setAttribute('cx', points.at(-1)[0]); this.field('point').setAttribute('cy', points.at(-1)[1]); }
    this.field('chartEmpty').hidden = values.length > 0;
    this.field('chartMax').textContent = high.toLocaleString();
    this.field('chartMin').textContent = low.toLocaleString();
    for (const [name, value] of [['min', Math.min(...values)], ['max', Math.max(...values)]]) {
      this.field(name).textContent = values.length ? `${value.toFixed(1)} ppm` : '—';
    }
    this.field('count').textContent = `${values.length} samples`;
  }
}
customElements.define('co2-sensor-panel', SensorPanel);

export function startSensorPolling(panel, { url = '/api/status', interval = 2000 } = {}) {
  let stopped = false, timer, controller;
  async function poll() {
    controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(url, { signal: controller.signal, cache: 'no-store' });
      if (!response.ok) throw new Error('Status unavailable');
      const data = await response.json();
      if (!Object.hasOwn(data, 'sensor')) throw new Error('Missing sensor state');
      if (!stopped) panel.update(data.sensor);
    } catch {
      if (!stopped) panel.unavailable();
    } finally {
      clearTimeout(timeout);
      if (!stopped) timer = setTimeout(poll, interval);
    }
  }
  poll();
  return () => { stopped = true; clearTimeout(timer); controller?.abort(); };
}
