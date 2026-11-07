/** Render only safe QKDKeyPool.get_status() fields. The shared app owns fetching. */
export function renderKeyPanel(container, status, { state = "ready" } = {}) {
  const doc = container.ownerDocument;
  const panel = doc.createElement("section");
  panel.className = "qts-key-panel";
  panel.setAttribute("aria-label", "Emulated key supply");
  const style = doc.createElement("style");
  style.textContent = `
    .qts-key-panel { color:#172d40; background:#fff; border:1px solid #cfdde6;
      border-radius:16px; padding:24px; font:16px/1.5 system-ui,sans-serif; }
    .qts-key-panel h2 { margin:0 0 4px; font-size:22px; }
    .qts-key-panel p { margin:8px 0; }
    .qts-key-panel .qts-key-subtitle { color:#516778; font-size:14px; }
    .qts-key-panel .qts-key-state { display:inline-block; padding:4px 12px;
      border-radius:6px; background:#e4edf3; font-weight:650; }
    .qts-key-panel[data-supply="enabled"] .qts-key-state { background:#d7f3e7; color:#10563f; }
    .qts-key-panel[data-supply="interrupted"] .qts-key-state { background:#fff0cd; color:#684800; }
    .qts-key-panel[data-supply="enabled"][data-full="true"] .qts-key-state { background:#e5eaff; color:#283d78; }
    .qts-key-panel .qts-key-occupancy { display:block; margin:12px 0; font-size:14px; }
    .qts-key-panel meter { display:block; width:100%; height:20px; }
    .qts-key-panel dl { display:grid; grid-template-columns:repeat(3,minmax(0,1fr));
      gap:12px; margin:20px 0; }
    .qts-key-panel dl div { background:#f3f7fa; padding:12px; border-radius:8px; }
    .qts-key-panel dt { font-size:13px; color:#516778; }
    .qts-key-panel dd { font-size:30px; font-weight:700; margin:0; }
    @media(max-width:420px) { .qts-key-panel { padding:16px; }
      .qts-key-panel dl { gap:6px; } .qts-key-panel dl div { padding:8px; } }
  `;
  const add = (tag, text, className) => {
    const element = doc.createElement(tag);
    element.textContent = text;
    if (className) element.className = className;
    panel.append(element);
    return element;
  };
  panel.append(style);
  add("h2", "Emulated key supply");
  add("p", "Classical secure randomness · software model", "qts-key-subtitle");
  const indicator = add("p", "", "qts-key-state");
  indicator.setAttribute("role", "status");
  const countNames = ["keys_available", "keys_generated", "keys_consumed"];
  const hasCapacity = status && Number.isSafeInteger(status.capacity) && status.capacity > 0;
  const valid = status && typeof status.supply_enabled === "boolean" &&
    countNames.every(name => Number.isSafeInteger(status[name]) && status[name] >= 0) &&
    status.keys_generated === status.keys_available + status.keys_consumed &&
    (!hasCapacity || status.keys_available <= status.capacity);
  if (state === "loading") {
    indicator.textContent = "Loading key supply…";
    add("p", "Waiting for backend status.");
  } else if (state === "disconnected") {
    indicator.textContent = "Backend disconnected";
    add("p", "Live counts are unavailable. Reconnect to refresh the pool state.");
  } else if (!valid || state !== "ready") {
    indicator.textContent = "Key supply unavailable";
    add("p", "No valid pool status has been received.");
  } else {
    panel.dataset.supply = status.supply_enabled ? "enabled" : "interrupted";
    const full = hasCapacity && status.keys_available === status.capacity;
    panel.dataset.full = String(full);
    indicator.textContent = !status.supply_enabled ? "Supply interrupted"
      : full ? "Pool full · generation waiting" : "Supply enabled";
    const counts = doc.createElement("dl");
    for (const [name, label] of [["keys_available", "Available"],
      ["keys_generated", "Generated"], ["keys_consumed", "Consumed"]]) {
      const group = doc.createElement("div");
      const term = doc.createElement("dt");
      term.textContent = label;
      const value = doc.createElement("dd");
      value.textContent = String(status[name]);
      group.append(term, value);
      counts.append(group);
    }
    panel.append(counts);
    if (hasCapacity) {
      for (const name of ["Device-side pool", "Twin-side pool"]) {
        const label = add("label", `${name}: ${status.keys_available} / ${status.capacity} keys`,
          "qts-key-occupancy");
        const meter = doc.createElement("meter");
        meter.min = 0;
        meter.max = status.capacity;
        meter.value = status.keys_available;
        meter.setAttribute("aria-label", name);
        label.append(meter);
      }
    }
    add("p", full
      ? "Both pools are full. No additional keys are accepted until allocation frees a slot."
      : status.keys_available === 0
      ? (status.supply_enabled
        ? "Pool empty. Waiting for automatic key supply before a new connection epoch."
        : "Pool empty. Resume supply to replenish keys automatically.")
      : "Queued keys are available for new connection epochs.");
    add("p", "Interrupting supply stops generation. Existing connection epochs remain usable.",
      "qts-key-subtitle");
  }
  container.replaceChildren(panel);
}
