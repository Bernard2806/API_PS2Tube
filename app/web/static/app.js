const API = "/api/v1/sessions";
const code = decodeURIComponent(
  location.pathname.split("/").filter(Boolean).pop() || ""
);
let sessionId = null;
let busy = false;

const STATUS_LABEL = {
  queued: "En cola",
  converting: "Convirtiendo",
  ready: "Listo",
  playing: "Reproduciendo",
  done: "Reproducido",
  failed: "Error",
};

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : "Error");
  }
  return res.json();
}

function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2500);
}

async function ensureSession() {
  if (sessionId) return sessionId;
  const session = await api(`${API}/code/${code}`);
  sessionId = session.id;
  document.getElementById("code").textContent = session.code;
  return sessionId;
}

function button(label, onClick) {
  const el = document.createElement("button");
  el.textContent = label;
  el.addEventListener("click", () => guard(onClick));
  return el;
}

function guard(fn) {
  return async () => {
    if (busy) return;
    busy = true;
    try {
      await fn();
    } catch (error) {
      toast(error.message);
    } finally {
      busy = false;
      await refresh();
    }
  };
}

async function playNow(id) {
  await ensureSession();
  await api(`${API}/${sessionId}/queue/${id}/play`, { method: "POST" });
}

async function removeItem(id) {
  await ensureSession();
  await api(`${API}/${sessionId}/queue/${id}`, { method: "DELETE" });
}

async function move(id, items, delta) {
  await ensureSession();
  const ids = items.map((item) => item.id);
  const index = ids.indexOf(id);
  const target = index + delta;
  if (target < 0 || target >= ids.length) return;
  [ids[index], ids[target]] = [ids[target], ids[index]];
  await api(`${API}/${sessionId}/queue/reorder`, {
    method: "POST",
    body: JSON.stringify({ item_ids: ids }),
  });
}

async function addUrls() {
  await ensureSession();
  const textarea = document.getElementById("urls");
  const urls = textarea.value
    .split(/\s+/)
    .map((value) => value.trim())
    .filter(Boolean);
  if (!urls.length) return;
  await api(`${API}/${sessionId}/queue`, {
    method: "POST",
    body: JSON.stringify({ urls }),
  });
  textarea.value = "";
  toast("Agregado a la cola");
}

function itemEl(item, items) {
  const li = document.createElement("li");
  li.className = `item ${item.status}`;

  const title = document.createElement("div");
  title.className = "title";
  title.textContent = item.title || item.url;
  li.appendChild(title);

  const meta = document.createElement("div");
  meta.className = "meta";
  const badge = document.createElement("span");
  badge.className = "badge";
  badge.textContent = STATUS_LABEL[item.status] || item.status;
  meta.appendChild(badge);
  if (item.status === "converting") {
    const pct = document.createElement("span");
    pct.textContent = `${Math.round((item.progress || 0) * 100)}%`;
    meta.appendChild(pct);
  }
  if (item.error) {
    const error = document.createElement("span");
    error.className = "error";
    error.textContent = item.error;
    meta.appendChild(error);
  }
  li.appendChild(meta);

  if (item.status !== "done" && item.status !== "failed") {
    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("div");
    fill.style.width = `${Math.round((item.progress || 0) * 100)}%`;
    bar.appendChild(fill);
    li.appendChild(bar);
  }

  const actions = document.createElement("div");
  actions.className = "actions";
  actions.appendChild(button("Reproducir", () => playNow(item.id)));
  actions.appendChild(button("Subir", () => move(item.id, items, -1)));
  actions.appendChild(button("Bajar", () => move(item.id, items, 1)));
  actions.appendChild(button("Borrar", () => removeItem(item.id)));
  li.appendChild(actions);

  return li;
}

function render(items) {
  const queue = document.getElementById("queue");
  queue.textContent = "";
  const sorted = [...items].sort((a, b) => a.position - b.position);

  const current =
    sorted.find((item) => item.status === "playing") ||
    sorted.find((item) => item.status === "ready");
  const now = document.getElementById("now");
  now.textContent = current
    ? current.title || current.url
    : "Nada en reproduccion";
  now.classList.toggle("empty", !current);

  if (!sorted.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "La cola esta vacia";
    queue.appendChild(empty);
    return;
  }
  sorted.forEach((item) => queue.appendChild(itemEl(item, sorted)));
}

async function refresh() {
  try {
    await ensureSession();
    render(await api(`${API}/${sessionId}/queue`));
  } catch (error) {
    toast(error.message);
  }
}

document.getElementById("add").addEventListener("click", guard(addUrls));
refresh();
setInterval(() => {
  if (!busy) refresh();
}, 2500);
