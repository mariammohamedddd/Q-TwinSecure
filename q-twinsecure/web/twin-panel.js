/* Owner component: Nancy's app calls panel.update(apiStatus.twin).
   null means no accepted observation; disconnected() preserves no live claim. */
(function (global) {
  'use strict';
  function mountTwinPanel(root, options = {}) {
    const doc = root.ownerDocument;
    root.replaceChildren();
    const section = doc.createElement('section');
    section.setAttribute('aria-label', 'Digital Twin freshness');
    section.setAttribute('class', 'twin-card' + (options.fullScreen ? ' twin-immersive' : ''));
    const title = doc.createElement('h2');
    title.textContent = 'Factory floor / Digital Twin';
    const layout = doc.createElement('div'); layout.setAttribute('class', 'twin-layout');
    const blueprint = doc.createElement('figure'); blueprint.setAttribute('class', 'twin-blueprint');
    const mapHeading = doc.createElement('div'); mapHeading.setAttribute('class', 'twin-map-heading');
    mapHeading.textContent = 'Plant 01 · Ground floor';
    const mapTag = doc.createElement('span'); mapTag.textContent = 'Illustrative 3D model'; mapHeading.append(mapTag);
    const viewport = doc.createElement('div'); viewport.setAttribute('class', 'twin-viewport');
    viewport.setAttribute('role', 'img');
    viewport.setAttribute('aria-label', '3D cutaway factory model with production machines, storage crates, control room and a red glowing demonstration sensor.');
    const scene = doc.createElement('div'); scene.setAttribute('class', 'twin-scene');
    function box(x, y, w, d, h, color, kind = '') {
      const solid = doc.createElement('div'); solid.setAttribute('class', 'twin-solid ' + kind);
      Object.assign(solid.style, {left:`${x}px`, top:`${y}px`, width:`${w}px`, height:`${d}px`});
      for (const [key, value] of Object.entries({'--w':`${w}px`, '--d':`${d}px`, '--h':`${h}px`, '--surface':color})) solid.style.setProperty(key, value);
      for (const side of ['top','front','back','left','right']) {
        const face = doc.createElement('div'); face.setAttribute('class', 'twin-face twin-face-' + side); solid.append(face);
      }
      scene.append(solid);
    }
    // Actual CSS 3D geometry: every machine has separate top and side faces.
    box(0, 0, 480, 360, 8, '#617e8c', 'twin-base');
    box(0, 0, 480, 7, 86, '#afc5ca');
    box(0, 0, 7, 360, 86, '#afc5ca');
    box(355, 8, 5, 230, 48, '#9eb9c1');
    for (const x of [75, 215]) {
      box(x, 65, 56, 172, 16, '#344d62');
      for (const y of [80, 139, 198]) box(x - 10, y, 76, 36, 43, '#71b5b2');
    }
    for (const x of [380, 430]) {
      for (const y of [55, 115, 175]) box(x, y, 33, 40, 34, '#c7a47b');
    }
    box(20, 280, 105, 60, 53, '#7c98b1');
    box(37, 290, 68, 14, 62, '#294757');
    box(340, 285, 110, 44, 19, '#8497a4');
    const aisle = doc.createElement('div'); aisle.setAttribute('class', 'twin-aisle'); scene.append(aisle);
    for (const [label, x, y] of [['PRODUCTION',115,245],['STORAGE',370,235],['CONTROL',30,345],['LOADING',350,340]]) {
      const tag = doc.createElement('span'); tag.setAttribute('class', 'twin-zone');
      Object.assign(tag.style, {left:`${x}px`, top:`${y}px`}); tag.textContent = label; scene.append(tag);
    }
    const sensor = doc.createElement('div'); sensor.setAttribute('class', 'twin-sensor');
    const pin = doc.createElement('span'); pin.setAttribute('class', 'twin-sensor-light');
    const sensorLabel = doc.createElement('span'); sensorLabel.setAttribute('class', 'twin-sensor-label');
    sensorLabel.textContent = 'CO₂ SENSOR 01'; sensor.append(pin, sensorLabel); scene.append(sensor);
    viewport.append(scene);
    const controls = doc.createElement('div'); controls.setAttribute('class', 'twin-model-controls');
    let angle = -35;
    let zoom = 1;
    const zoomLabel = doc.createElement('span'); zoomLabel.setAttribute('class', 'twin-zoom-label');
    zoomLabel.setAttribute('aria-live', 'polite');
    function camera() {
      scene.style.setProperty('--rotation', `${angle}deg`);
      scene.style.setProperty('--zoom', String(zoom));
      zoomLabel.textContent = `${Math.round(zoom * 100)}%`;
    }
    function changeZoom(delta) { zoom = Math.max(.5, Math.min(3, zoom + delta)); camera(); }
    for (const [label, delta] of [['Rotate left',-45],['Reset view',0],['Rotate right',45]]) {
      const button = doc.createElement('button'); button.setAttribute('type', 'button'); button.textContent = label;
      button.onclick = () => {
        angle = delta === 0 ? -35 : angle + delta;
        if (delta === 0) zoom = 1;
        camera();
      };
      controls.append(button);
    }
    for (const [label, delta] of [['− Zoom out',-.15],['+ Zoom in',.15]]) {
      const button = doc.createElement('button'); button.setAttribute('type', 'button'); button.textContent = label;
      button.onclick = () => changeZoom(delta); controls.append(button);
    }
    controls.append(zoomLabel);
    // Wheel zoom is scoped to the factory surface so information remains scrollable.
    viewport.onwheel = (event) => { event.preventDefault(); changeZoom(event.deltaY < 0 ? .08 : -.08); };
    let drag = null;
    viewport.onpointerdown = (event) => {
      if (event.button !== 0) return;
      drag = {x:event.clientX, angle}; viewport.setPointerCapture(event.pointerId);
    };
    viewport.onpointermove = (event) => {
      if (!drag) return;
      angle = drag.angle + (event.clientX - drag.x) * .4; camera();
    };
    viewport.onpointerup = viewport.onpointercancel = () => { drag = null; };
    zoomLabel.textContent = '100%';
    const legend = doc.createElement('figcaption');
    legend.textContent = '● Red glow = sensor location for visual demonstration only. It does not indicate danger, freshness or a live physical sensor. Factory geometry and sensor placement are illustrative.';
    blueprint.append(mapHeading, viewport, controls, legend);
    const readingDetails = doc.createElement('div'); readingDetails.setAttribute('class', 'twin-reading-details');
    const badge = doc.createElement('p');
    badge.setAttribute('role', 'status');
    badge.setAttribute('aria-live', 'polite');
    badge.setAttribute('class', 'twin-badge');
    const explanation = doc.createElement('p');
    explanation.setAttribute('class', 'twin-explanation');
    const details = doc.createElement('dl');
    const fields = {};
    for (const [key, label] of Object.entries({value_ppm:'Latest CO₂ reading', age_seconds:'Time since measurement', sensor_id:'Sensor source', timestamp:'Measured at', received_at:'Received by the Twin', thresholds:'How freshness is calculated'})) {
      const group = doc.createElement('div');
      group.setAttribute('class', 'twin-field' + (['value_ppm','age_seconds'].includes(key) ? ' metric' : '') + (key === 'thresholds' ? ' wide' : ''));
      const term = doc.createElement('dt'); term.textContent = label;
      const value = doc.createElement('dd');
      if (key === 'thresholds') {
        const track = doc.createElement('div'); track.setAttribute('class', 'twin-track');
        for (const color of ['#30a58a','#e7b557','#dc7b7b']) {
          const segment = doc.createElement('span'); segment.style.background = color; track.append(segment);
        }
        group.append(track);
      }
      fields[key] = value; group.append(term, value); details.append(group);
    }
    const note = doc.createElement('p');
    note.setAttribute('class', 'twin-note');
    note.textContent = 'Freshness describes data age, not CO₂ safety. An expired reading remains visible as the last known value.';
    readingDetails.append(badge, explanation, details, note);
    layout.append(blueprint, readingDetails);
    section.append(title, layout); root.append(section);
    function readableTime(value) {
      if (!value) return '—';
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return 'Unavailable';
      return new Intl.DateTimeFormat('en-GB', {
        day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit',
        second:'2-digit', hour12:true, timeZoneName:'short',
      }).format(date);
    }
    function clear(label) {
      badge.textContent = label; badge.style.color = '#526078';
      badge.style.background = '#f1f5f8';
      explanation.textContent = label.startsWith('Disconnected') ? 'The preview cannot reach the monitor. Check that the Python server is running.' : 'Send a sample reading to start monitoring. Its age and freshness will appear here.';
      for (const field of Object.values(fields)) field.textContent = '—';
    }
    clear('Loading Twin status…');
    return {
      update(status) {
        if (status == null) { clear('MISSING — no accepted observation yet'); return; }
        if (!['CURRENT','DELAYED','MISSING'].includes(status.freshness)) {
          clear('Twin status unavailable'); return;
        }
        const hasReading = status.timestamp != null;
        badge.textContent = status.freshness + (hasReading ? '' : ' — no accepted observation yet');
        badge.style.color = {CURRENT:'#166534',DELAYED:'#854d0e',MISSING:'#b91c1c'}[status.freshness];
        badge.style.background = {CURRENT:'#e7f5ef',DELAYED:'#fff3d8',MISSING:'#fcebea'}[status.freshness];
        explanation.textContent = !hasReading ? 'No reading has arrived yet. Send your first sample to see the Twin update.' : {
          CURRENT:'Your latest reading is fresh. The Twin has a recent view of this sensor.',
          DELAYED:'The latest reading is getting old. The Twin is waiting for a newer measurement.',
          MISSING:'No recent reading is available. The value below is the last known measurement.',
        }[status.freshness];
        fields.sensor_id.textContent = status.sensor_id ?? '—';
        fields.value_ppm.textContent = status.value_ppm == null ? '—' : `${status.value_ppm} ppm`;
        fields.timestamp.textContent = readableTime(status.timestamp);
        fields.received_at.textContent = readableTime(status.received_at);
        fields.timestamp.setAttribute('title', status.timestamp ?? 'No measurement yet');
        fields.received_at.setAttribute('title', status.received_at ?? 'No receipt yet');
        fields.age_seconds.textContent = Number.isFinite(status.age_seconds) ? `${status.age_seconds.toFixed(1)} seconds` : '—';
        fields.thresholds.textContent = `CURRENT ≤ ${status.current_threshold}s · DELAYED ≤ ${status.missing_threshold}s · MISSING > ${status.missing_threshold}s`;
      },
      disconnected() { clear('Disconnected — live Twin status unavailable'); },
    };
  }
  global.mountTwinPanel = mountTwinPanel;
})(globalThis);
