// The shared dashboard supplies the gateway object from GET /api/status.
export function renderGatewayPanel(container, gateway) {
  container.replaceChildren();
  const title = document.createElement("h2");
  title.textContent = "Security gateway";
  container.append(title);

  const available = gateway && ["CONNECTED", "DISCONNECTED"].includes(gateway.connection_state);
  const rows = available
    ? [
        ["Connection", gateway.connection_state === "CONNECTED" ? "Connected" : "Disconnected"],
        ["Connection epoch", typeof gateway.connection_epoch === "string" ? gateway.connection_epoch : "None"],
        ["Latest verification", gateway.verification === "VERIFIED" ? "Verified" :
          gateway.verification === "REJECTED" ? "Rejected" : "No message verified yet"],
      ]
    : [["Status", "Gateway status unavailable"]];

  const list = document.createElement("dl");
  for (const [label, value] of rows) {
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value;
    list.append(term, description);
  }
  container.append(list);
}
