const agentsRoot = document.getElementById("agents");
const logsRoot = document.getElementById("logs");
const detailsRoot = document.getElementById("details");
const timelineRoot = document.getElementById("timeline");
const healthRoot = document.getElementById("health");
const filterTextInput = document.getElementById("filterText");
const filterStatusSelect = document.getElementById("filterStatus");
const filterErrorsOnlyInput = document.getElementById("filterErrorsOnly");

let latestSnapshot = {
  agents: [],
  logs: [],
  timeline: []
};
let latestHealth = {};

const statusClass = (status) => {
  return {
    running: "status-running",
    idle: "status-idle",
    error: "status-error",
    done: "status-done"
  }[status] || "";
};

function renderAgents(agents) {
  agentsRoot.innerHTML = "";
  if (agents.length === 0) {
    const li = document.createElement("li");
    li.className = "agent-item";
    li.innerHTML = `
      <div><strong>No agents matched</strong></div>
      <div class="label">Check filters or wait for new Pixel activity.</div>
    `;
    agentsRoot.appendChild(li);
    return;
  }
  for (const agent of agents) {
    const li = document.createElement("li");
    li.className = "agent-item";
    li.innerHTML = `
      <div><strong>${agent.agent_id}</strong></div>
      <div class="status ${statusClass(agent.status)}">${agent.status}</div>
      <div>${agent.task}</div>
      <div class="label">${agent.last_update}</div>
    `;
    li.onclick = () => renderDetails(agent);
    agentsRoot.appendChild(li);
  }
}

function renderLogs(logs) {
  const latest = logs.slice(-250);
  const lines = latest.map((event) => {
    const css = event.status === "error" ? "log-error" : "";
    return `<span class="${css}">[${event.timestamp}] [${event.source}] [${event.agent_id}] ${event.task} :: ${event.log}</span>`;
  });
  logsRoot.innerHTML = lines.join("\n");
}

function renderTimeline(timeline) {
  timelineRoot.innerHTML = "";
  const latest = timeline.slice(-120).reverse();
  for (const item of latest) {
    const li = document.createElement("li");
    li.className = "timeline-item";
    li.innerHTML = `
      <div><span class="status ${statusClass(item.status)}">${item.status}</span> ${item.task}</div>
      <div>${item.agent_id}</div>
      <div class="label">${item.timestamp} (${item.source})</div>
    `;
    timelineRoot.appendChild(li);
  }
}

function renderDetails(agent) {
  detailsRoot.innerHTML = `
    <div class="details-grid">
      <div class="label">Agent</div><div>${agent.agent_id}</div>
      <div class="label">Status</div><div class="status ${statusClass(agent.status)}">${agent.status}</div>
      <div class="label">Task</div><div>${agent.task}</div>
      <div class="label">Last update</div><div>${agent.last_update}</div>
      <div class="label">Source</div><div>${agent.last_source}</div>
    </div>
  `;
}

function renderHealth(health) {
  healthRoot.innerHTML = `
    <div>file: ${health.fileWatcher ? "ok" : "down"}</div>
    <div>ws: ${health.websocket ? "ok" : "down"}</div>
    <div>commands: ${health.commandScan ? "ok" : "down"}</div>
  `;
}

function getFilters() {
  return {
    text: (filterTextInput.value || "").trim().toLowerCase(),
    status: filterStatusSelect.value,
    errorsOnly: Boolean(filterErrorsOnlyInput.checked)
  };
}

function matchByText(eventOrAgent, text) {
  if (!text) {
    return true;
  }
  const haystack = [eventOrAgent.agent_id, eventOrAgent.task, eventOrAgent.log || ""].join(" ").toLowerCase();
  return haystack.includes(text);
}

function matchByStatus(eventOrAgent, status) {
  if (!status || status === "all") {
    return true;
  }
  return eventOrAgent.status === status;
}

function applyFilters(snapshot) {
  const filters = getFilters();
  const logFiltered = snapshot.logs.filter((event) => {
    if (filters.errorsOnly && event.status !== "error") {
      return false;
    }
    return matchByStatus(event, filters.status) && matchByText(event, filters.text);
  });

  const timelineFiltered = snapshot.timeline.filter((event) => {
    if (filters.errorsOnly && event.status !== "error") {
      return false;
    }
    return matchByStatus(event, filters.status) && matchByText(event, filters.text);
  });

  const agentsFiltered = snapshot.agents.filter((agent) => {
    if (filters.errorsOnly && agent.status !== "error") {
      return false;
    }
    return matchByStatus(agent, filters.status) && matchByText(agent, filters.text);
  });

  return {
    agents: agentsFiltered,
    logs: logFiltered,
    timeline: timelineFiltered
  };
}

function rerender() {
  const filtered = applyFilters(latestSnapshot);
  renderAgents(filtered.agents);
  renderLogs(filtered.logs);
  renderTimeline(filtered.timeline);
  renderHealth(latestHealth);
  if (filtered.agents.length > 0) {
    renderDetails(filtered.agents[0]);
  } else {
    detailsRoot.innerHTML = '<div class="label">No agent matches the current filters.</div>';
  }
}

window.addEventListener("message", (message) => {
  const payload = message.data;
  if (payload.type !== "snapshot") {
    return;
  }
  latestSnapshot = payload.payload;
  latestHealth = payload.health;
  rerender();
});

[filterTextInput, filterStatusSelect, filterErrorsOnlyInput].forEach((el) => {
  el.addEventListener("input", rerender);
  el.addEventListener("change", rerender);
});
