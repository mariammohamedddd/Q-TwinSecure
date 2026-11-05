/* Owner component: Nancy's app calls panel.update(apiStatus.twin).
   null means no accepted observation; disconnected() preserves no live claim. */
(function (global) {
  'use strict';
  function mountTwinPanel(root) {
    const doc = root.ownerDocument;
    root.replaceChildren();
    const section = doc.createElement('section');
    section.setAttribute('aria-label', 'Digital Twin freshness');
    section.setAttribute('class', 'twin-card');
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
      @media(max-width:560px){.twin-card{padding:22px}.twin-card dl{grid-template-columns:1fr}.twin-field.wide{grid-column:auto}.twin-field.metric dd{font-size:30px}}
    `;
    const title = doc.createElement('h2');
    title.textContent = 'Digital Twin';
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
    section.append(title, badge, explanation, details, note); root.append(style, section);
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
        fields.timestamp.textContent = status.timestamp ?? '—';
        fields.received_at.textContent = status.received_at ?? '—';
        fields.age_seconds.textContent = Number.isFinite(status.age_seconds) ? `${status.age_seconds.toFixed(1)} seconds` : '—';
        fields.thresholds.textContent = `CURRENT ≤ ${status.current_threshold}s · DELAYED ≤ ${status.missing_threshold}s · MISSING > ${status.missing_threshold}s`;
      },
      disconnected() { clear('Disconnected — live Twin status unavailable'); },
    };
  }
  global.mountTwinPanel = mountTwinPanel;
})(globalThis);
