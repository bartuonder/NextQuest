/* NextQuest web client - no framework, no build step. */

const TOKEN_KEY = "nextquest.token";
const $ = (selector) => document.querySelector(selector);

const state = {
  token: localStorage.getItem(TOKEN_KEY),
  info: null,
  user: null,
};

/* ------------------------------------------------------------- helpers -- */

class ApiError extends Error {}

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && state.token) headers.Authorization = `Bearer ${state.token}`;

  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401 && auth) {
    logout();
    throw new ApiError("Your session expired. Please log in again.");
  }
  if (response.status === 204) return null;

  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(detailOf(payload) || `Request failed (${response.status}).`);
  return payload;
}

function detailOf(payload) {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(" · ");
  return null;
}

let toastTimer;
function toast(message, kind = "error") {
  const el = $("#toast");
  el.textContent = message;
  el.className = `toast ${kind}`;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 5000);
}

/** Slug used by TasteProfile: game -> games, tv_series -> tv_series, anime -> animes. */
function tasteKey(category) {
  return { game: "games", movie: "movies", book: "books", tv_series: "tv_series", anime: "animes" }[category];
}

/* ---------------------------------------------------------------- auth -- */

function setSession(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem(TOKEN_KEY, token);
  render();
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem(TOKEN_KEY);
  render();
}

function render() {
  const authed = Boolean(state.token && state.user);
  $("#auth-view").hidden = authed;
  $("#app-view").hidden = !authed;
  $("#logout-btn").hidden = !authed;
  $("#user-chip").hidden = !authed;
  if (authed) $("#user-chip").textContent = `@${state.user.username}`;
}

/* ---------------------------------------------------------- taste form -- */

function buildTasteFields() {
  const container = $("#taste-fields");
  container.innerHTML = "";
  for (const { value, label } of state.info.categories) {
    const group = document.createElement("div");
    group.className = "taste-group";
    group.innerHTML = `<h3>${label}</h3>`;
    for (let i = 0; i < state.info.samples_per_category; i += 1) {
      const input = document.createElement("input");
      input.dataset.category = value;
      input.placeholder = `${label} #${i + 1}`;
      input.maxLength = 200;
      group.appendChild(input);
    }
    container.appendChild(group);
  }
}

function readTaste() {
  const taste = {};
  for (const { value } of state.info.categories) taste[tasteKey(value)] = [];
  document.querySelectorAll("#taste-fields input").forEach((input) => {
    const title = input.value.trim();
    if (title) taste[tasteKey(input.dataset.category)].push(title);
  });
  return taste;
}

function fillTaste(taste) {
  const cursors = {};
  document.querySelectorAll("#taste-fields input").forEach((input) => {
    const key = tasteKey(input.dataset.category);
    const index = cursors[key] ?? 0;
    cursors[key] = index + 1;
    input.value = taste[key]?.[index] ?? "";
  });
}

function hasAnyTaste(taste) {
  return Object.values(taste).some((titles) => titles.length > 0);
}

/* -------------------------------------------------------------- render -- */

function renderBatch(batch) {
  $("#result").hidden = false;
  $("#result-summary").textContent = batch.summary ?? "";
  $("#result-meta").textContent = `${batch.model} · ${new Date(batch.created_at).toLocaleString()}`;

  const labels = Object.fromEntries(state.info.categories.map((c) => [c.value, c.label]));
  const groups = new Map();
  for (const item of batch.items) {
    if (!groups.has(item.category)) groups.set(item.category, []);
    groups.get(item.category).push(item);
  }

  const container = $("#result-groups");
  container.innerHTML = "";
  for (const [category, items] of groups) {
    const section = document.createElement("section");
    section.className = "group";
    section.innerHTML = `<h3>${labels[category] ?? category}</h3><div class="cards"></div>`;
    const cards = section.querySelector(".cards");
    for (const item of items) cards.appendChild(recommendationCard(item));
    container.appendChild(section);
  }
  $("#result").scrollIntoView({ behavior: "smooth", block: "start" });
}

function recommendationCard(item) {
  const card = document.createElement("article");
  card.className = "rec";

  const head = document.createElement("div");
  head.className = "rec-head";
  const title = document.createElement("div");
  title.className = "rec-title";
  title.textContent = item.title;
  if (item.year) {
    const year = document.createElement("span");
    year.className = "rec-year";
    year.textContent = ` (${item.year})`;
    title.appendChild(year);
  }
  const score = document.createElement("span");
  score.className = "score";
  score.textContent = `${item.match_score}%`;
  head.append(title, score);

  const reason = document.createElement("p");
  reason.className = "rec-reason";
  reason.textContent = item.reason;

  const tags = document.createElement("div");
  tags.className = "tags";
  for (const tag of item.tags ?? []) {
    const chip = document.createElement("span");
    chip.className = "tag";
    chip.textContent = tag;
    tags.appendChild(chip);
  }

  card.append(head, reason, tags);
  return card;
}

async function loadHistory() {
  const list = $("#history-list");
  let batches;
  try {
    batches = await api("/recommendations?limit=20");
  } catch (error) {
    toast(error.message);
    return;
  }

  list.innerHTML = "";
  if (!batches.length) {
    list.innerHTML = '<li class="empty">No runs yet. Fill in your taste and hit the button.</li>';
    return;
  }

  for (const batch of batches) {
    const row = document.createElement("li");
    const info = document.createElement("div");
    info.innerHTML = `<div>${batch.items.length} picks</div>
      <div class="meta">${new Date(batch.created_at).toLocaleString()}${batch.mood ? ` · ${batch.mood}` : ""}</div>`;
    info.onclick = () => renderBatch(batch);

    const remove = document.createElement("button");
    remove.className = "btn icon";
    remove.textContent = "✕";
    remove.title = "Delete this run";
    remove.onclick = async (event) => {
      event.stopPropagation();
      try {
        await api(`/recommendations/${batch.id}`, { method: "DELETE" });
        loadHistory();
      } catch (error) {
        toast(error.message);
      }
    };

    row.append(info, remove);
    list.appendChild(row);
  }
}

/* --------------------------------------------------------------- boot -- */

document.querySelectorAll("[data-auth-tab]").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll("[data-auth-tab]").forEach((other) => other.classList.remove("active"));
    tab.classList.add("active");
    const login = tab.dataset.authTab === "login";
    $("#login-form").hidden = !login;
    $("#register-form").hidden = login;
  };
});

$("#login-form").onsubmit = async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    const data = await api("/auth/login", {
      method: "POST",
      auth: false,
      body: { username: form.get("username"), password: form.get("password") },
    });
    setSession(data.access_token, data.user);
    await afterLogin();
  } catch (error) {
    toast(error.message);
  }
};

$("#register-form").onsubmit = async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    const data = await api("/auth/register", {
      method: "POST",
      auth: false,
      body: {
        username: form.get("username"),
        email: form.get("email"),
        password: form.get("password"),
        full_name: form.get("full_name") || null,
      },
    });
    setSession(data.access_token, data.user);
    toast(`Welcome aboard, ${data.user.username}!`, "success");
    await afterLogin();
  } catch (error) {
    toast(error.message);
  }
};

$("#logout-btn").onclick = logout;
$("#refresh-history").onclick = loadHistory;

$("#save-taste-btn").onclick = async () => {
  const taste = readTaste();
  if (!hasAnyTaste(taste)) return toast("Add at least one title first.");
  try {
    await api("/favorites/taste", { method: "PUT", body: taste });
    toast("Taste profile saved.", "success");
  } catch (error) {
    toast(error.message);
  }
};

$("#taste-form").onsubmit = async (event) => {
  event.preventDefault();
  const taste = readTaste();
  if (!hasAnyTaste(taste)) return toast("Add at least one title first.");

  const button = $("#generate-btn");
  button.disabled = true;
  $("#loading").hidden = false;
  $("#result").hidden = true;

  try {
    const batch = await api("/recommendations", {
      method: "POST",
      body: {
        taste,
        mood: $("#mood").value.trim() || null,
        per_category: Number($("#per-category").value),
        save_favorites: true,
      },
    });
    renderBatch(batch);
    loadHistory();
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    $("#loading").hidden = true;
  }
};

async function afterLogin() {
  try {
    fillTaste(await api("/favorites/taste"));
  } catch {
    /* a fresh account simply has nothing saved yet */
  }
  loadHistory();
}

async function boot() {
  try {
    state.info = await api("/meta", { auth: false });
  } catch {
    toast("Cannot reach the NextQuest API.");
    return;
  }

  $("#samples-hint").textContent = state.info.samples_per_category;
  const badge = $("#llm-badge");
  badge.hidden = false;
  badge.className = `badge ${state.info.llm_enabled ? "on" : "off"}`;
  badge.textContent = state.info.llm_enabled ? state.info.llm_model : "no API key";

  buildTasteFields();

  if (state.token) {
    try {
      state.user = await api("/auth/me");
      render();
      await afterLogin();
      return;
    } catch {
      logout();
      return;
    }
  }
  render();
}

boot();
