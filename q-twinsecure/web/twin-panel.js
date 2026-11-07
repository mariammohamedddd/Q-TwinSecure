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
    const style = doc.createElement('style');
    style.textContent = `
      .twin-card{font:15px system-ui,sans-serif;background:white;border:1px solid #e0e7ed;border-radius:22px;padding:32px;color:#162b36;box-shadow:0 10px 40px #1b344508}
      .twin-card *{box-sizing:border-box}.twin-card h2{font-size:12px;text-transform:uppercase;letter-spacing:2px;color:#637785;margin:0 0 18px}
      .twin-badge{display:inline-flex;padding:7px 12px;border-radius:8px;background:#f1f5f8;font-size:12px;font-weight:750;letter-spacing:.5px;margin:0}
      .twin-explanation{font-size:16px;line-height:1.6;color:#536773;max-width:660px;margin:16px 0 26px}
      .twin-card dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 32px;margin:0}
      .twin-field{padding:19px 0;border-top:1px solid #edf1f4;min-width:0}.twin-field dt{font-size:12px;color:#607581;margin-bottom:8px}
      .twin-field dd{margin:0;font-size:15px;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
      .twin-field.metric dd{font-size:36px;letter-spacing:-1.5px;font-weight:650;line-height:1.3}
      .twin-field.wide{grid-column:1/-1}.twin-track{display:flex;gap:6px;margin:4px 0 8px;height:7px}
      .twin-track span{flex:1;border-radius:4px}.twin-note{font-size:12px;color:#6b7e89;line-height:1.7;margin:22px 0 0;padding-top:18px;border-top:1px solid #edf1f4}
      .twin-layout{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(300px,1fr);gap:28px;align-items:start}
      .twin-blueprint{margin:0;background:#0c253c;border:1px solid #254a67;border-radius:16px;overflow:hidden;position:relative}
      .twin-blueprint img{display:block;width:100%;height:auto}.twin-blueprint figcaption{padding:16px 20px;border-top:1px solid #254a67;color:#acc7dc;font-size:12px;line-height:1.7}
      .twin-map-heading{display:flex;justify-content:space-between;gap:12px;padding:18px 20px;color:#e4f0fb;font-size:11px;letter-spacing:1px;text-transform:uppercase}
      .twin-map-heading span{color:#86a8c4}.twin-reading-details{min-width:0}.twin-reading-details .twin-explanation{font-size:14px;margin:14px 0 22px}
      .twin-reading-details .twin-field.metric dd{font-size:30px}.twin-reading-details .twin-field dd{font-size:14px}.twin-reading-details .twin-field.metric dd{font-size:30px}
      .twin-viewport{height:460px;position:relative;overflow:hidden;perspective:1000px;background:radial-gradient(ellipse at 50% 45%,#234c63,#0c253c 75%)}
      .twin-scene{position:absolute;left:50%;top:49%;width:480px;height:360px;transform-style:preserve-3d;transform:translate(-50%,-50%) rotateX(58deg) rotateZ(var(--rotation,-35deg)) scale(calc(.8 * var(--zoom,1)))}
      .twin-solid{position:absolute;transform-style:preserve-3d}.twin-face{position:absolute;background:var(--surface);border:1px solid #233e4933;transform-origin:0 0;backface-visibility:visible}
      .twin-face-top{width:var(--w);height:var(--d);transform:translateZ(var(--h));background:linear-gradient(135deg,#ffffff30,#00000008),var(--surface)}
      .twin-face-front,.twin-face-back{width:var(--w);height:var(--h);filter:brightness(.78)}
      .twin-face-front{transform:translateY(var(--d)) rotateX(90deg)}.twin-face-back{transform:rotateX(90deg)}
      .twin-face-left,.twin-face-right{width:var(--h);height:var(--d);filter:brightness(.57)}
      .twin-face-left{transform:rotateY(-90deg)}.twin-face-right{transform:translateX(var(--w)) rotateY(-90deg)}
      .twin-base .twin-face-top{background:repeating-linear-gradient(0deg,transparent 0 29px,#b9ced529 29px 30px),repeating-linear-gradient(90deg,#617e8c 0 29px,#b9ced544 29px 30px)}
      .twin-aisle{position:absolute;left:12px;top:263px;width:455px;height:3px;background:repeating-linear-gradient(90deg,#f2ce70 0 15px,transparent 15px 25px);transform:translateZ(9px)}
      .twin-zone{position:absolute;color:#e7f4fc;font:9px system-ui;letter-spacing:1px;transform:translateZ(10px)}
      .twin-sensor{position:absolute;left:172px;top:145px;transform:translateZ(65px);transform-style:preserve-3d}
      .twin-sensor-light{display:block;width:15px;height:15px;border-radius:50%;background:#ff435a;border:2px solid #ffc0c8;box-shadow:0 0 0 9px #ff435a25,0 0 0 20px #ff435a12,0 0 28px 10px #ff435a99}
      .twin-sensor-label{position:absolute;left:22px;top:-8px;white-space:nowrap;color:#ffd2d8;background:#572d3c;padding:6px 8px;border:1px solid #e37a8b;border-radius:4px;font:10px system-ui;transform:rotateZ(35deg)}
      .twin-model-controls{display:flex;gap:8px;padding:0 18px 16px;flex-wrap:wrap}.twin-model-controls button{width:auto;margin:0;padding:9px 12px;border:1px solid #476b83;border-radius:7px;background:#183b53;color:#daecf9;font:12px system-ui;cursor:pointer}.twin-model-controls button:hover{background:#2a506b}.twin-model-controls button:focus-visible{outline:2px solid #75d8c4;outline-offset:3px}
      @media(max-width:560px){.twin-scene{transform:translate(-50%,-50%) rotateX(58deg) rotateZ(var(--rotation,-35deg)) scale(calc(.55 * var(--zoom,1)))}.twin-viewport{height:330px}}

      @media(max-width:1050px){.twin-layout{grid-template-columns:1fr}.twin-blueprint img{max-height:520px}.twin-reading-details .twin-field.metric dd{font-size:32px}}
      @media(max-width:560px){.twin-card{padding:22px}.twin-card dl{grid-template-columns:1fr}.twin-field.wide{grid-column:auto}.twin-field.metric dd{font-size:30px}}
      .twin-immersive{position:fixed;inset:0;padding:0;border:0;border-radius:0;background:#0c253c;box-shadow:none}
      .twin-immersive>h2{display:none}.twin-immersive .twin-layout{display:block;height:100%}
      .twin-immersive .twin-blueprint{position:absolute;inset:0;border:0;border-radius:0;background:transparent}
      .twin-immersive .twin-viewport{position:absolute;inset:0;height:100%;touch-action:none;cursor:grab;perspective:1500px}
      .twin-immersive .twin-viewport:active{cursor:grabbing}
      .twin-immersive .twin-scene{left:38%;top:51%;--fit:1.5;transform:translate(-50%,-50%) rotateX(58deg) rotateZ(var(--rotation,-35deg)) scale(calc(var(--fit) * var(--zoom,1)))}
      .twin-immersive .twin-map-heading{position:absolute;left:28px;top:95px;z-index:2;display:block;padding:0;pointer-events:none;font-size:13px}
      .twin-immersive .twin-map-heading span{display:block;margin-top:9px;font-size:10px}
      .twin-immersive .twin-reading-details{position:absolute;right:24px;top:95px;bottom:100px;width:340px;overflow:auto;padding:24px;border:1px solid #56768c66;border-radius:18px;background:#f7fbf9f2;box-shadow:0 20px 60px #0004;z-index:3}
      .twin-immersive .twin-reading-details dl{gap:0 18px}.twin-immersive .twin-field{padding:14px 0}.twin-immersive .twin-note{margin-top:14px}
      .twin-immersive .twin-model-controls{position:absolute;z-index:4;bottom:24px;left:50%;transform:translateX(-50%);padding:10px;justify-content:center;background:#0d293ce8;border:1px solid #456177;border-radius:14px;flex-wrap:nowrap;max-width:calc(100% - 28px)}
      .twin-immersive .twin-model-controls button{white-space:nowrap;padding:11px}.twin-zoom-label{color:#dceef8;align-self:center;font:12px system-ui;min-width:40px;text-align:center}
      .twin-immersive figcaption{position:absolute;left:28px;bottom:104px;max-width:300px;border:0;background:#102d3cdb;padding:12px 15px;border-radius:10px;font-size:11px;pointer-events:none}
      @media(max-width:1100px){.twin-immersive .twin-scene{left:30%;--fit:1.05}.twin-immersive .twin-reading-details{width:300px;right:16px}}
      @media(max-width:700px){.twin-immersive .twin-scene{left:50%;top:30%;--fit:.78}.twin-immersive .twin-reading-details{top:auto;bottom:96px;left:12px;right:12px;width:auto;max-height:32vh;padding:16px}.twin-immersive .twin-reading-details dl{grid-template-columns:1fr 1fr}.twin-immersive .twin-field.wide{grid-column:1/-1}.twin-immersive .twin-map-heading{left:16px;top:78px}.twin-immersive figcaption{bottom:auto;top:119px;left:16px;max-width:230px;font-size:10px;padding:7px}.twin-immersive .twin-model-controls{bottom:16px;flex-wrap:wrap;width:max-content;gap:5px}.twin-immersive .twin-model-controls button{padding:9px;font-size:11px}}
    `;
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
      solid.style.cssText = `left:${x}px;top:${y}px;width:${w}px;height:${d}px;--w:${w}px;--d:${d}px;--h:${h}px;--surface:${color}`;
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
      tag.style.cssText = `left:${x}px;top:${y}px`; tag.textContent = label; scene.append(tag);
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
    section.append(title, layout); root.append(style, section);
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
