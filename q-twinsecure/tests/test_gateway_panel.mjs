import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import test from "node:test";

// Load the browser ES module without requiring a project-wide Node configuration.
const source = await readFile(new URL("../web/gateway-panel.js", import.meta.url), "utf8");
const { renderGatewayPanel } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

class Element {
  constructor() { this.children = []; this.textContent = ""; }
  append(...children) { this.children.push(...children); }
  replaceChildren() { this.children = []; }
}
globalThis.document = { createElement: () => new Element() };
const text = element => [element.textContent, ...element.children.flatMap(child => text(child))];

test("renders actual backend snapshot without treating it as delivery", () => {
  const python = process.env.PYTHON || "python";
  const script = [
    "import json, secrets",
    "from gateway.crypto import encrypt_reading",
    "from gateway.status import GatewayStatus",
    "g=GatewayStatus(); g.start_epoch('epoch-1'); k=secrets.token_bytes(32)",
    "r={'sensor_id':'sensor','value_ppm':650,'timestamp':'2026-11-05T12:30:00+00:00'}",
    "g.verify_reading(encrypt_reading(r,k),k)",
    "print(json.dumps(g.get_status()))",
  ].join("; ");
  const status = JSON.parse(execFileSync(python, ["-B", "-c", script], { encoding: "utf8" }));
  const container = new Element();
  renderGatewayPanel(container, status);
  assert.ok(text(container).includes("Connected"));
  assert.ok(text(container).includes("Verified"));
  assert.ok(text(container).includes("epoch-1"));
  assert.ok(!text(container).includes("Delivered"));
  renderGatewayPanel(container, { ...status, verification: "REJECTED" });
  assert.ok(text(container).includes("Rejected"));
  renderGatewayPanel(container, null);
  assert.ok(text(container).includes("Gateway status unavailable"));
});
