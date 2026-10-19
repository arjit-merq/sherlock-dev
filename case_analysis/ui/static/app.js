const state = {
  runs: [],
  health: null,
  automatic: null,
  activeTab: window.location.hash.replace("#", "") || "manual",
};

const icons = {
  report: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l3 3v15H6zM14 3v4h4M9 12h6M9 16h6M9 8h2"/></svg>',
  copy: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>',
  empty: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v14H4zM8 9h8M8 13h5"/></svg>',
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

const SAFE_URL_RE = /^(https?:|mailto:)/i;

/* Reports are local markdown, but they quote Jira and log text verbatim, so every
   value goes in as a text node and link targets are scheme-checked. */
function appendInline(parent, text) {
  const pattern = /`([^`]+)`|\*\*([\s\S]+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)|\*([^*\n]+)\*/g;
  let cursor = 0;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      parent.append(document.createTextNode(text.slice(cursor, match.index)));
    }
    if (match[1] !== undefined) {
      parent.append(element("code", "", match[1]));
    } else if (match[2] !== undefined) {
      const strong = element("strong");
      appendInline(strong, match[2]);
      parent.append(strong);
    } else if (match[3] !== undefined && SAFE_URL_RE.test(match[4])) {
      const link = element("a");
      link.href = match[4];
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      appendInline(link, match[3]);
      parent.append(link);
    } else if (match[5] !== undefined) {
      const emphasis = element("em");
      appendInline(emphasis, match[5]);
      parent.append(emphasis);
    } else {
      parent.append(document.createTextNode(match[0]));
    }
    cursor = pattern.lastIndex;
  }
  if (cursor < text.length) parent.append(document.createTextNode(text.slice(cursor)));
}

function tableCells(line) {
  return line
    .replace(/^\s*\|/, "")
    .replace(/\|\s*$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isTableSeparator(line) {
  return line.includes("-") && /^\s*\|?[\s:|-]+$/.test(line);
}

function renderMarkdown(markdown) {
  const fragment = document.createDocumentFragment();
  const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const paragraph = [];
  let index = 0;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const node = element("p");
    appendInline(node, paragraph.join(" "));
    fragment.append(node);
    paragraph.length = 0;
  };

  while (index < lines.length) {
    const line = lines[index];
    const fence = line.match(/^\s*```(\w*)\s*$/);
    if (fence) {
      flushParagraph();
      const body = [];
      index += 1;
      while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
        body.push(lines[index]);
        index += 1;
      }
      index += 1;
      const block = element("pre", "report-code");
      block.append(element("code", "", body.join("\n")));
      fragment.append(block);
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      index += 1;
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flushParagraph();
      const level = Math.min(heading[1].length, 3);
      const tag = level === 1 ? "h3" : level === 2 ? "h4" : "h5";
      const node = element(tag, `report-heading report-heading--${level}`);
      appendInline(node, heading[2].trim());
      fragment.append(node);
      index += 1;
      continue;
    }

    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      flushParagraph();
      fragment.append(element("hr"));
      index += 1;
      continue;
    }

    if (line.trim().startsWith("|") && isTableSeparator(lines[index + 1] || "")) {
      flushParagraph();
      const table = element("table", "report-table");
      const head = element("thead");
      const headRow = element("tr");
      tableCells(line).forEach((cell) => {
        const th = element("th");
        appendInline(th, cell);
        headRow.append(th);
      });
      head.append(headRow);
      table.append(head);
      index += 2;
      const body = element("tbody");
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        const row = element("tr");
        tableCells(lines[index]).forEach((cell) => {
          const cellNode = element("td");
          appendInline(cellNode, cell);
          row.append(cellNode);
        });
        body.append(row);
        index += 1;
      }
      table.append(body);
      const wrapper = element("div", "report-table-wrap");
      wrapper.append(table);
      fragment.append(wrapper);
      continue;
    }

    const bulletPattern = /^\s*[-*+]\s+(.*)$/;
    const orderedPattern = /^\s*\d+[.)]\s+(.*)$/;
    const isBullet = bulletPattern.test(line);
    if (isBullet || orderedPattern.test(line)) {
      flushParagraph();
      const itemPattern = isBullet ? bulletPattern : orderedPattern;
      const list = element(isBullet ? "ul" : "ol", "report-list");
      while (index < lines.length) {
        const current = lines[index];
        const item = current.match(itemPattern);
        if (item) {
          const listItem = element("li");
          appendInline(listItem, item[1].trim());
          list.append(listItem);
          index += 1;
          continue;
        }
        // Wrapped continuation of the previous bullet, not a new block.
        if (current.trim() && /^\s{2,}\S/.test(current) && list.lastElementChild) {
          list.lastElementChild.append(document.createTextNode(` ${current.trim()}`));
          index += 1;
          continue;
        }
        break;
      }
      fragment.append(list);
      continue;
    }

    const quote = line.match(/^\s*>\s?(.*)$/);
    if (quote) {
      flushParagraph();
      const buffer = [quote[1]];
      index += 1;
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
        buffer.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      const block = element("blockquote", "report-quote");
      appendInline(block, buffer.join(" "));
      fragment.append(block);
      continue;
    }

    paragraph.push(line.trim());
    index += 1;
  }

  flushParagraph();
  return fragment;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `Request failed with status ${response.status}.`);
  }
  return payload;
}

function formatTime(value, includeDate = false) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    ...(includeDate ? { month: "short", day: "numeric" } : {}),
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatDuration(seconds) {
  if (seconds >= 60 && seconds % 60 === 0) return `${seconds / 60} min`;
  return `${seconds} sec`;
}

let toastTimer;
function showToast(message) {
  const toast = document.querySelector("#toast");
  document.querySelector("#toast-message").textContent = message;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.hidden = true;
  }, 6000);
}

function setButtonLoading(button, loading, label) {
  button.disabled = loading;
  button.dataset.state = loading ? "loading" : "default";
  const labelNode = button.querySelector("span");
  if (labelNode) labelNode.textContent = label;
}

function selectTab(name, updateHash = true) {
  const validName = ["manual", "automatic", "capabilities", "history"].includes(name) ? name : "manual";
  state.activeTab = validName;
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab.dataset.tab === validName;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll(".page-panel").forEach((panel) => {
    const active = panel.id === `panel-${validName}`;
    panel.hidden = !active;
    panel.classList.toggle("is-active", active);
  });
  if (updateHash) history.replaceState(null, "", `#${validName}`);
}

function statusBadge(run) {
  let modifier = "active";
  let label = "In progress";
  if (run.stage_index >= 6) {
    modifier = "complete";
    label = "Complete";
  } else if (run.status.toLowerCase().includes("failed")) {
    modifier = "failed";
    label = "Failed";
  }
  return element("span", `badge badge--${modifier}`, label);
}

function stageTrack(index) {
  const track = element("div", "stage-track");
  track.setAttribute("aria-label", `Stage ${Math.min(index, 6)} of 6`);
  for (let step = 1; step <= 6; step += 1) {
    const segment = document.createElement("span");
    segment.classList.toggle("is-done", step <= index);
    track.append(segment);
  }
  return track;
}

function emptyState(title, detail) {
  const wrapper = element("div", "empty-state");
  wrapper.innerHTML = icons.empty;
  wrapper.append(element("strong", "", title), element("p", "", detail));
  return wrapper;
}

function createRunCard(run) {
  const card = element("article", `run-card${run.active ? " is-active" : ""}`);

  const identity = element("div", "run-card__identity");
  const identityText = element("div");
  identityText.append(
    element("h3", "", run.issue_key),
    element("time", "", `Started ${formatTime(run.started_at, true)}`),
    element("small", "", run.mode === "optimized" ? "Optimized investigation" : "Standard investigation"),
  );
  identity.append(identityText, statusBadge(run));

  const stage = element("div", "run-card__stage");
  const stageName = element("p", "stage-name");
  stageName.append(
    element("span", "stage-index", `${String(Math.min(run.stage_index, 6)).padStart(2, "0")}/06`),
    element("span", "", run.stage),
  );
  stage.append(stageName, stageTrack(run.stage_index));

  const actions = element("div", "run-actions");
  if (run.report_file) {
    const reportButton = element("button", "button button--quiet");
    reportButton.type = "button";
    reportButton.innerHTML = `${icons.report}<span>View report</span>`;
    reportButton.addEventListener("click", () => openReport(run));
    actions.append(reportButton);
  }

  card.append(identity, stage, actions);
  return card;
}

const RECENT_RUN_WINDOW_MS = 30 * 60 * 1000;

/* The backend only tracks processes this console launched, so a run that outlived a
   console restart needs a time window to still count as in flight. Without the window,
   a run whose agent died without writing a terminal status looks active forever. */
function isRunInFlight(run) {
  if (run.active) return true;
  if (run.status.toLowerCase().includes("failed") || run.stage_index >= 6) return false;
  if (run.finished_at || run.report_file) return false;
  const startedAt = new Date(run.started_at).getTime();
  return Number.isFinite(startedAt) && Date.now() - startedAt < RECENT_RUN_WINDOW_MS;
}

function renderCurrentRuns() {
  const container = document.querySelector("#current-runs");
  const activeRuns = state.runs.filter(isRunInFlight);
  document.querySelector("#active-count").textContent = String(activeRuns.length);
  container.replaceChildren();
  if (!activeRuns.length) {
    container.append(
      emptyState(
        "No investigation is running.",
        "Start one above, or let automatic polling wait for a new PES case.",
      ),
    );
    return;
  }
  activeRuns.forEach((run) => container.append(createRunCard(run)));
}

function historyMatches(run) {
  if (run.stage_index < 6 || run.status.toLowerCase().includes("failed")) return false;
  const query = document.querySelector("#history-search").value.trim().toUpperCase();
  if (query && !run.issue_key.includes(query) && !run.run_id.toUpperCase().includes(query)) return false;
  return true;
}

function createHistoryRow(run) {
  const row = element("article", "history-row");
  const identity = element("div", "history-row__identity");
  identity.append(element("div", "history-row__key", run.issue_key), statusBadge(run));

  const details = element("div");
  details.append(element("div", "history-row__stage", run.stage));
  const meta = element("div", "history-row__meta");
  meta.append(
    element("span", "", formatTime(run.started_at, true)),
    element("span", "", run.mode),
    element("span", "", run.report_file || "No report"),
  );
  details.append(meta);

  const actions = element("div", "history-row__actions");
  if (run.report_file) {
    const viewButton = element("button", "button button--quiet");
    viewButton.type = "button";
    viewButton.innerHTML = `${icons.report}<span>View</span>`;
    viewButton.addEventListener("click", () => openReport(run));
    actions.append(viewButton);
  }
  const copyButton = element("button", "icon-button");
  copyButton.type = "button";
  copyButton.setAttribute("aria-label", `Copy artifact path for ${run.issue_key}`);
  copyButton.innerHTML = icons.copy;
  copyButton.addEventListener("click", async () => {
    await navigator.clipboard.writeText(run.path);
    showToast(`Copied artifact path for ${run.issue_key}.`);
  });
  actions.append(copyButton);

  row.append(identity, details, actions);
  return row;
}

function renderHistory() {
  const container = document.querySelector("#history-list");
  const filtered = state.runs.filter(historyMatches);
  container.replaceChildren();
  if (!filtered.length) {
    container.append(emptyState("No matching completed runs.", "Change the case filter, or finish an investigation first."));
    return;
  }
  filtered.forEach((run) => container.append(createHistoryRow(run)));
}

function renderHealth() {
  if (!state.health) return;
  const systemState = document.querySelector("#system-state");
  const dot = systemState.querySelector(".status-dot");
  const missing = [];
  if (!state.health.agent_available) missing.push("Agent CLI");
  if (!state.health.merq_creds_available) missing.push("MerQ creds");
  if (!state.health.jira_configured) missing.push("Jira");
  dot.className = `status-dot ${missing.length ? "status-dot--warn" : "status-dot--good"}`;
  systemState.querySelector("span:last-child").textContent = missing.length
    ? `Check ${missing.join(", ")}`
    : "Local services ready";
}

function renderAutomatic() {
  if (!state.automatic) return;
  const automatic = state.automatic;
  document.querySelector("#auto-state-label").textContent = automatic.enabled ? "Polling active" : "Polling paused";
  document.querySelector("#auto-toggle").setAttribute("aria-checked", String(automatic.enabled));
  document.querySelector("#auto-tab-signal").classList.toggle("is-on", automatic.enabled);
  document.querySelector("#poll-interval").textContent = formatDuration(automatic.interval_seconds);
  document.querySelector("#poll-delay").textContent = formatDuration(automatic.delay_seconds);
  document.querySelector("#known-count").textContent = String(automatic.known_open_cases);
  document.querySelector("#last-check").textContent = automatic.last_check
    ? formatTime(automatic.last_check)
    : "Not yet";
  document.querySelector("#poll-health").textContent = automatic.last_error
    ? "Last check failed"
    : automatic.last_check
      ? "Jira responded"
      : "Waiting for first poll";

  const error = document.querySelector("#auto-error");
  error.hidden = !automatic.last_error && automatic.configured;
  document.querySelector("#auto-error-text").textContent =
    automatic.last_error || "Add JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN to case_analysis/.env.";

  const queue = document.querySelector("#auto-queue");
  queue.replaceChildren();
  if (!automatic.queued.length) {
    queue.append(
      emptyState(
        "No new cases are queued.",
        automatic.enabled ? "The poller is watching Jira." : "Resume polling to watch for new cases.",
      ),
    );
    return;
  }
  automatic.queued.forEach((item) => {
    const row = element("article", "queue-item");
    const details = element("div");
    details.append(element("h3", "", item.issue_key), element("p", "", item.summary || "No Jira summary"));
    const due = element("time", "", `Due ${formatTime(item.due_at)}`);
    row.append(details, due);
    queue.append(row);
  });
}

async function refreshData() {
  try {
    const [runsPayload, health, automatic] = await Promise.all([
      api("/api/runs"),
      api("/api/health"),
      api("/api/automatic"),
    ]);
    state.runs = runsPayload.runs;
    state.health = health;
    state.automatic = automatic;
    renderCurrentRuns();
    renderHistory();
    renderHealth();
    renderAutomatic();
  } catch (error) {
    showToast(error.message);
  }
}

async function openReport(run) {
  const dialog = document.querySelector("#report-dialog");
  const content = document.querySelector("#report-content");
  content.replaceChildren(element("p", "report-status", "Loading report…"));
  document.querySelector("#report-title").textContent = run.issue_key;
  document.querySelector("#report-kind").textContent = run.report_file || "Report";
  dialog.showModal();
  try {
    const report = await api(`/api/runs/${encodeURIComponent(run.run_id)}/report`);
    document.querySelector("#report-kind").textContent = report.filename;
    content.replaceChildren(renderMarkdown(report.content));
    content.scrollTop = 0;
  } catch (error) {
    content.replaceChildren(element("p", "report-status", error.message));
  }
}

async function launchInvestigation(event) {
  event.preventDefault();
  const caseInput = document.querySelector("#case-input");
  const caseField = caseInput.closest(".field");
  const help = document.querySelector("#case-help");
  const button = document.querySelector("#launch-button");
  const value = caseInput.value.trim();
  caseField.classList.remove("has-error");
  help.textContent = "Bare numbers default to PES.";
  if (!value) {
    caseField.classList.add("has-error");
    help.textContent = "Enter a PES or ENG case before starting.";
    caseInput.setAttribute("aria-invalid", "true");
    caseInput.focus();
    return;
  }
  caseInput.removeAttribute("aria-invalid");
  setButtonLoading(button, true, "Starting investigation");
  try {
    const result = await api("/api/investigations", {
      method: "POST",
      body: JSON.stringify({
        case: value,
        context: document.querySelector("#context-input").value,
      }),
    });
    showToast(`${result.issue_key} investigation started.`);
    caseInput.value = "";
    document.querySelector("#context-input").value = "";
    setTimeout(refreshData, 800);
  } catch (error) {
    caseField.classList.add("has-error");
    help.textContent = error.message;
    caseInput.setAttribute("aria-invalid", "true");
    caseInput.focus();
  } finally {
    setButtonLoading(button, false, "Start investigation");
  }
}

async function toggleAutomatic() {
  const enabled = document.querySelector("#auto-toggle").getAttribute("aria-checked") === "true";
  try {
    state.automatic = await api(`/api/automatic/${enabled ? "stop" : "start"}`, {
      method: "POST",
      body: "{}",
    });
    renderAutomatic();
  } catch (error) {
    showToast(error.message);
  }
}

async function pollNow() {
  const button = document.querySelector("#poll-now");
  button.disabled = true;
  try {
    state.automatic = await api("/api/automatic/poll", { method: "POST", body: "{}" });
    renderAutomatic();
  } catch (error) {
    showToast(error.message);
    await refreshData();
  } finally {
    button.disabled = false;
  }
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => selectTab(tab.dataset.tab));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    const tabs = [...document.querySelectorAll(".tab")];
    const direction = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (tabs.indexOf(tab) + direction + tabs.length) % tabs.length;
    tabs[nextIndex].focus({ preventScroll: true });
    selectTab(tabs[nextIndex].dataset.tab);
  });
});

document.querySelector("#launch-form").addEventListener("submit", launchInvestigation);
document.querySelector("#refresh-runs").addEventListener("click", refreshData);
document.querySelector("#auto-toggle").addEventListener("click", toggleAutomatic);
document.querySelector("#poll-now").addEventListener("click", pollNow);
document.querySelector("#history-search").addEventListener("input", renderHistory);
document.querySelector("#close-report").addEventListener("click", () => {
  document.querySelector("#report-dialog").close();
});
document.querySelector("#report-dialog").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) event.currentTarget.close();
});
document.querySelector("#toast-close").addEventListener("click", () => {
  document.querySelector("#toast").hidden = true;
});

selectTab(state.activeTab, false);
refreshData();
setInterval(refreshData, 3000);
