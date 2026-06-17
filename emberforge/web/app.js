const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const msg = data?.detail || data?.message || res.statusText;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

function toast(message, kind = "ok") {
  const el = $("#toast");
  el.textContent = message;
  el.className = `toast ${kind}`;
  el.hidden = false;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.hidden = true; }, 3200);
}

function showView(name) {
  $$(".view").forEach((v) => v.classList.remove("active"));
  $$(".nav-item").forEach((n) => n.classList.remove("active"));
  $(`#view-${name}`)?.classList.add("active");
  $(`.nav-item[data-view="${name}"]`)?.classList.add("active");
  history.replaceState(null, "", `#${name}`);
}

function initNav() {
  $$(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.view));
  });
  const hash = location.hash.replace("#", "") || "dashboard";
  if ($(`#view-${hash}`)) showView(hash);
  else showView("dashboard");
}

function renderDashboard(status) {
  const banner = $("#ready-banner");
  if (status.ready) {
    banner.className = "status-banner ready";
    banner.textContent = "Ready to serve — configuration looks good.";
  } else if (status.issues?.length) {
    banner.className = "status-banner error";
    banner.textContent = status.issues.join(" · ");
  } else {
    banner.className = "status-banner warn";
    banner.textContent = (status.warnings || []).join(" · ") || "Needs attention.";
  }

  const cards = [
    { label: "API key", value: status.api_key_set ? "Set" : "Missing" },
    { label: "Context", value: status.context_enabled ? "On" : "Off" },
    { label: "Location", value: status.context_location_configured ? (status.location?.name || "Set") : "Not set" },
    { label: "RSS feeds", value: String(status.rss_feed_count || 0) },
    { label: "Personas", value: (status.personas || []).join(", ") || "—" },
    { label: "Paired devices", value: String(status.paired_device_count || 0) },
    { label: "TOTP", value: status.totp_configured ? "Configured" : "Not set" },
    { label: "Environment", value: status.ember_env || "development" },
  ];

  $("#dashboard-cards").innerHTML = cards
    .map((c) => `<div class="card stat-card"><div class="value">${escapeHtml(c.value)}</div><div class="label">${escapeHtml(c.label)}</div></div>`)
    .join("");

  $("#version-label").textContent = `v${status.version || "?"}`;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

let _lastSetupStatus = null;

async function loadStatus() {
  const status = await api("/setup/v1/status");
  _lastSetupStatus = status;
  renderDashboard(status);
  updateChatVoiceHint(status);
  return status;
}

function updateChatVoiceHint(status) {
  const hint = $("#chat-voice-hint");
  if (!hint) return;
  if (status?.server_tts_available) {
    hint.textContent = "ElevenLabs will play in the browser. Without it, macOS say plays on this hub's speakers.";
  } else {
    hint.textContent = "No ElevenLabs key — responses use macOS say on this hub, or browser speech if unavailable.";
  }
}

function updateLlmProviderHint() {
  const provider = $("#llm-provider")?.value || "grok";
  const hint = $("#llm-provider-hint");
  const model = $("#llm-model");
  if (!hint) return;
  if (provider === "claude") {
    hint.textContent = "Claude uses ANTHROPIC_API_KEY. Default model: claude-sonnet-4-6.";
    if (model && (!model.value || model.value.startsWith("grok"))) {
      model.placeholder = "claude-sonnet-4-6";
    }
  } else {
    hint.textContent = "Grok uses XAI_API_KEY. Default model: grok-3-latest.";
    if (model && model.placeholder === "claude-sonnet-4-6") {
      model.placeholder = "grok-3-latest";
    }
  }
}

async function loadConfig() {
  const { values } = await api("/setup/v1/config");
  const form = $("#keys-form");
  for (const [key, val] of Object.entries(values)) {
    const input = form.querySelector(`[name="${key}"]`);
    if (!input || !val) continue;
    if (input.tagName === "SELECT") {
      input.value = val;
    } else if (val.startsWith("••••")) {
      input.placeholder = val;
    } else if (!input.value) {
      input.placeholder = val;
    }
  }
  updateLlmProviderHint();
  $("#rss-feeds").value = values.EMBER_RSS_FEEDS || "";
  $("#context-enabled").checked = values.EMBER_CONTEXT_ENABLED === "true";
  if (values.EMBER_ADMIN_TOTP_SECRET && !$("#totp-secret").value) {
    $("#totp-uri").textContent = values.EMBER_ADMIN_TOTP_SECRET.startsWith("••••")
      ? "TOTP secret is configured (masked)."
      : values.EMBER_ADMIN_TOTP_SECRET;
  }
}

async function loadProfile() {
  const { content } = await api("/setup/v1/profile");
  $("#profile-content").value = content || "";
}

const CHAT_SESSION_STORAGE_KEY = "emberforge-setup-chat-session";

let _chatSessionId = newChatSessionId();
let _chatSessionPersona = null;

function newChatSessionId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function updateChatSessionHint(turns) {
  const hint = $("#chat-session-hint");
  if (!hint) return;
  hint.textContent =
    turns > 0
      ? `${turns} turn${turns === 1 ? "" : "s"} in this session`
      : "New session — context builds as you chat";
}

function persistChatSession() {
  try {
    sessionStorage.setItem(
      CHAT_SESSION_STORAGE_KEY,
      JSON.stringify({ sessionId: _chatSessionId, persona: _chatSessionPersona }),
    );
  } catch {
    /* private browsing / storage full */
  }
}

function restoreChatSession() {
  try {
    const raw = sessionStorage.getItem(CHAT_SESSION_STORAGE_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (saved.sessionId) _chatSessionId = saved.sessionId;
    if (saved.persona) _chatSessionPersona = saved.persona;
  } catch {
    /* ignore corrupt storage */
  }
}

function resetChatSession({ clearLog = false, announce = true } = {}) {
  _chatSessionId = newChatSessionId();
  _chatSessionPersona = $("#test-persona")?.value || null;
  persistChatSession();
  updateChatSessionHint(0);
  if (clearLog) $("#chat-log").innerHTML = "";
  if (announce) toast("New conversation");
}

async function loadPersonas() {
  const data = await api("/personas");
  const select = $("#test-persona");
  select.innerHTML = (data.personas || [])
    .map((p) => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`)
    .join("");
  if (_chatSessionPersona && data.personas?.some((p) => p.id === _chatSessionPersona)) {
    select.value = _chatSessionPersona;
  } else if (data.default) {
    select.value = data.default;
  }
  _chatSessionPersona = select.value;
  persistChatSession();
}

async function loadDevices() {
  const data = await api("/admin/v1/devices");
  const list = $("#device-list");
  const devices = data.devices || [];
  if (!devices.length) {
    list.innerHTML = '<p class="hint">No paired devices yet.</p>';
    return;
  }
  list.innerHTML = devices
    .map(
      (d) => `
      <div class="device-row">
        <div>
          <strong>${escapeHtml(d.name)}</strong>
          <div class="hint">${escapeHtml(d.device_id)} · ${escapeHtml(d.paired_at || "")}</div>
        </div>
        <button type="button" data-revoke="${escapeHtml(d.device_id)}">Revoke</button>
      </div>`
    )
    .join("");

  list.querySelectorAll("[data-revoke]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm(`Revoke device ${btn.dataset.revoke}?`)) return;
      try {
        await api(`/admin/v1/devices/${encodeURIComponent(btn.dataset.revoke)}`, { method: "DELETE" });
        toast("Device revoked");
        await loadDevices();
        await loadStatus();
      } catch (err) {
        toast(err.message, "error");
      }
    });
  });
}

$("#llm-provider")?.addEventListener("change", updateLlmProviderHint);

$("#keys-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const values = {};
  for (const [key, val] of fd.entries()) {
    if (String(val).trim()) values[key] = String(val).trim();
  }
  try {
    await api("/setup/v1/config", { method: "PATCH", body: JSON.stringify({ values }) });
    $("#keys-status").textContent = "Saved.";
    toast("API keys saved");
    e.target.reset();
    await loadConfig();
    await loadStatus();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#location-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = new FormData(e.target).get("query");
  try {
    const data = await api("/setup/v1/location/search", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
    const box = $("#location-matches");
    if (!data.matches?.length) {
      box.innerHTML = '<p class="hint">No matches — try just the city name.</p>';
      return;
    }
    box.innerHTML = data.matches
      .map(
        (m) => `
        <div class="match-item">
          <span>${escapeHtml(m.name)}</span>
          <button type="button" class="btn" data-index="${m.index}" data-query="${escapeHtml(data.query)}">Use</button>
        </div>`
      )
      .join("");
    box.querySelectorAll("[data-index]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const saved = await api("/setup/v1/location", {
            method: "POST",
            body: JSON.stringify({ query: btn.dataset.query, index: Number(btn.dataset.index) }),
          });
          $("#location-status").textContent = `Saved: ${saved.location.name}`;
          toast("Location saved");
          await loadStatus();
        } catch (err) {
          toast(err.message, "error");
        }
      });
    });
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#save-context-btn")?.addEventListener("click", async () => {
  const values = {
    EMBER_RSS_FEEDS: $("#rss-feeds").value.trim(),
    EMBER_CONTEXT_ENABLED: $("#context-enabled").checked ? "true" : "false",
  };
  try {
    await api("/setup/v1/config", { method: "PATCH", body: JSON.stringify({ values }) });
    toast("Context settings saved");
    await loadStatus();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#save-profile-btn")?.addEventListener("click", async () => {
  try {
    await api("/setup/v1/profile", {
      method: "PUT",
      body: JSON.stringify({ content: $("#profile-content").value }),
    });
    $("#profile-status").textContent = "Saved.";
    toast("Profile saved");
  } catch (err) {
    toast(err.message, "error");
  }
});

let pairingTimer = null;

$("#pair-btn")?.addEventListener("click", async () => {
  try {
    const data = await api("/admin/v1/pair/code", { method: "POST" });
    $("#pairing-code").textContent = data.code;
    const expiry = Date.now() + data.expires_in * 1000;
    clearInterval(pairingTimer);
    pairingTimer = setInterval(() => {
      const left = Math.max(0, Math.ceil((expiry - Date.now()) / 1000));
      $("#pairing-expiry").textContent = left ? `Expires in ${left}s` : "Expired — generate a new code";
      if (!left) clearInterval(pairingTimer);
    }, 500);
    toast("Pairing code generated");
    await loadDevices();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#totp-generate-btn")?.addEventListener("click", async () => {
  try {
    const data = await api("/setup/v1/totp/generate", { method: "POST" });
    $("#totp-secret").value = data.secret;
    $("#totp-uri").textContent = data.provisioning_uri;
    toast("TOTP secret generated — save to .env");
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#totp-save-btn")?.addEventListener("click", async () => {
  const secret = $("#totp-secret").value.trim();
  if (!secret) {
    toast("Enter or generate a TOTP secret", "error");
    return;
  }
  try {
    await api("/setup/v1/config", {
      method: "PATCH",
      body: JSON.stringify({ values: { EMBER_ADMIN_TOTP_SECRET: secret } }),
    });
    toast("TOTP secret saved");
    await loadStatus();
  } catch (err) {
    toast(err.message, "error");
  }
});

const _chatPlayback = new Map();

function base64ToBlob(base64, mime) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

function stopSpeech() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();
}

function speakInBrowser(text) {
  if (!window.speechSynthesis || !text) return false;
  stopSpeech();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  window.speechSynthesis.speak(utterance);
  return true;
}

function voiceBadge(voice, mode) {
  if (mode === "mp3") return `🔊 ${voice?.provider || "audio"} · replay available`;
  if (mode === "hub") return `🔊 playing on hub (${voice?.voice || voice?.provider || "macOS say"})`;
  if (mode === "browser-tts") return "🔊 browser speech";
  return "";
}

function playChatVoice(bubbleId, voice, text) {
  const cached = _chatPlayback.get(bubbleId);
  if (cached?.type === "mp3" && cached.url) {
    stopSpeech();
    const audio = new Audio(cached.url);
    audio.play().catch(() => toast("Could not play audio", "error"));
    return;
  }
  if (voice?.audio_base64) {
    const fmt = voice.format || "mp3";
    const mime = fmt === "mp3" ? "audio/mpeg" : `audio/${fmt}`;
    const url = URL.createObjectURL(base64ToBlob(voice.audio_base64, mime));
    _chatPlayback.set(bubbleId, { type: "mp3", url, voice, text });
    stopSpeech();
    const audio = new Audio(url);
    audio.play().catch(() => toast("Could not play audio", "error"));
    return;
  }
  if (voice?.played_locally) {
    speakInBrowser(text);
    return;
  }
  speakInBrowser(text);
}

function appendAssistantBubble(log, data) {
  const bubbleId = `bubble-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  const voice = data.voice || {};
  const text = data.response || "";
  let mode = "none";
  if (voice.audio_base64) mode = "mp3";
  else if (voice.played_locally) mode = "hub";
  else if ($("#chat-voice")?.checked) mode = "browser-tts";

  if (mode === "mp3") {
    const fmt = voice.format || "mp3";
    const mime = fmt === "mp3" ? "audio/mpeg" : `audio/${fmt}`;
    const url = URL.createObjectURL(base64ToBlob(voice.audio_base64, mime));
    _chatPlayback.set(bubbleId, { type: "mp3", url, voice, text });
  }

  const badge = voiceBadge(voice, mode);
  const replayBtn =
    $("#chat-voice")?.checked && mode !== "none"
      ? `<button type="button" class="btn-icon" data-replay="${bubbleId}" title="Replay">▶</button>`
      : "";

  log.innerHTML += `
    <div class="chat-bubble assistant" data-bubble="${bubbleId}">
      <div class="chat-bubble-head">
        <div class="who">${escapeHtml(data.persona_name || data.persona || "Ember")}</div>
        ${replayBtn}
      </div>
      <div>${escapeHtml(text)}</div>
      ${badge ? `<div class="voice-badge">${escapeHtml(badge)}</div>` : ""}
    </div>`;

  const replay = log.querySelector(`[data-replay="${bubbleId}"]`);
  replay?.addEventListener("click", () => playChatVoice(bubbleId, voice, text));

  if ($("#chat-voice")?.checked) {
    if (mode === "mp3") playChatVoice(bubbleId, voice, text);
    else if (mode === "hub") { /* already played on server */ }
    else if (mode === "browser-tts") speakInBrowser(text);
  }

  log.scrollTop = log.scrollHeight;
}

$("#test-persona")?.addEventListener("change", () => {
  const persona = $("#test-persona").value;
  if (_chatSessionPersona && persona !== _chatSessionPersona) {
    resetChatSession({ clearLog: true, announce: false });
    toast("Persona changed — fresh conversation");
  }
  _chatSessionPersona = persona;
  persistChatSession();
});

$("#chat-clear-btn")?.addEventListener("click", () => {
  resetChatSession({ clearLog: true });
});

$("#chat-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = $("#chat-message").value.trim();
  if (!message) return;
  const persona = $("#test-persona").value;
  const voiceEnabled = $("#chat-voice")?.checked ?? false;
  const log = $("#chat-log");
  log.innerHTML += `<div class="chat-bubble user"><div class="who">You</div>${escapeHtml(message)}</div>`;
  $("#chat-message").value = "";
  try {
    const data = await api("/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        persona,
        session_id: _chatSessionId,
        synthesize_audio: voiceEnabled,
        play_audio: voiceEnabled,
      }),
    });
    if (data.session_id) _chatSessionId = data.session_id;
    _chatSessionPersona = persona;
    persistChatSession();
    updateChatSessionHint(data.history_turns || 0);
    appendAssistantBubble(log, data);
  } catch (err) {
    log.innerHTML += `<div class="chat-bubble assistant"><div class="who">Error</div>${escapeHtml(err.message)}</div>`;
  }
});

async function boot() {
  initNav();
  restoreChatSession();
  try {
    await Promise.all([loadStatus(), loadConfig(), loadProfile(), loadPersonas(), loadDevices()]);
  } catch (err) {
    toast(`Setup load failed: ${err.message}`, "error");
  }
}

boot();