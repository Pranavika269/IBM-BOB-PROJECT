/* ProjectMatch front end: vanilla JS, no build step. */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const COLORS = ["#3355FF", "#0E8F6B", "#C8402C", "#7A45E5", "#B77900", "#0B8794"];

const state = { students: [], me: null, recs: [], selected: null, editingId: null, catalog: null };
let postSkills, postDomains, profSkills, profInterests;

/* ---------- helpers ---------- */
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const initials = n => n.split(/\s+/).map(w => w[0]).slice(0, 2).join("").toUpperCase();
const avatar = (p, cls = "") => `<span class="av ${cls}" style="background:${COLORS[p.id % COLORS.length]}" title="${esc(p.name)}">${esc(initials(p.name))}</span>`;
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const chips = (arr, cls = "") => arr.map(x => `<span class="chip ${cls}">${esc(x)}</span>`).join("");

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong. Try again.");
  return data;
}

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
}

/* ---------- tag input (skills, topics) ---------- */
function tagInput(root, { listId, placeholder }) {
  let tags = [];
  function draw(focus) {
    root.innerHTML = tags.map((t, i) =>
      `<span class="tag">${esc(t)}<button type="button" data-i="${i}" aria-label="Remove ${esc(t)}">×</button></span>`).join("") +
      `<input list="${listId}" placeholder="${tags.length ? "" : esc(placeholder)}" aria-label="${esc(placeholder)}">`;
    if (focus) $("input", root).focus();
  }
  function add(raw) {
    raw.split(",").map(s => s.trim()).filter(Boolean).forEach(s => {
      if (!tags.some(t => t.toLowerCase() === s.toLowerCase())) tags.push(s);
    });
    draw(true);
  }
  root.addEventListener("click", e => {
    const b = e.target.closest("button[data-i]");
    if (b) { tags.splice(+b.dataset.i, 1); draw(true); }
  });
  root.addEventListener("keydown", e => {
    if (e.target.tagName !== "INPUT") return;
    if ((e.key === "Enter" || e.key === ",") && e.target.value.trim()) { e.preventDefault(); add(e.target.value); }
    else if (e.key === "Enter") e.preventDefault();
    else if (e.key === "Backspace" && !e.target.value && tags.length) { tags.pop(); draw(true); }
  });
  root.addEventListener("change", e => { if (e.target.tagName === "INPUT" && e.target.value.trim()) add(e.target.value); });
  draw();
  return {
    get() { const i = $("input", root); if (i && i.value.trim()) add(i.value); return [...tags]; },
    set(arr) { tags = [...arr]; draw(); },
  };
}

/* ---------- navigation ---------- */
function showView(name) {
  $$(".view").forEach(v => v.hidden = v.id !== `view-${name}`);
  $$(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.view === name));
  if (name === "profile") fillProfile(state.me);
}
$(".tabs").addEventListener("click", e => {
  const b = e.target.closest("button[data-view]");
  if (b) showView(b.dataset.view);
});

/* ---------- boot ---------- */
async function boot() {
  const [students, catalog] = await Promise.all([api("/api/students"), api("/api/skills")]);
  state.students = students;
  state.catalog = catalog;
  $("#dl-skills").innerHTML = catalog.skills.map(s => `<option value="${esc(s.name)}">${esc(s.category)}</option>`).join("");
  $("#dl-domains").innerHTML = catalog.domains.map(d => `<option value="${esc(d)}">`).join("");
  postSkills = tagInput($("#post-skills"), { listId: "dl-skills", placeholder: "Add a skill" });
  postDomains = tagInput($("#post-domains"), { listId: "dl-domains", placeholder: "Add a topic" });
  profSkills = tagInput($("#profile-skills"), { listId: "dl-skills", placeholder: "Add a skill" });
  profInterests = tagInput($("#profile-interests"), { listId: "dl-domains", placeholder: "Add an interest" });

  let saved = null;
  try { saved = +localStorage.getItem("pm-me"); } catch (_) {}
  state.me = students.find(s => s.id === saved) || students[0];
  drawWho();
  await loadRecs();
}

function drawWho() {
  $("#who").innerHTML = state.students.map(s =>
    `<option value="${s.id}" ${s.id === state.me.id ? "selected" : ""}>${esc(s.name)}</option>`).join("");
}
$("#who").addEventListener("change", async e => {
  state.me = state.students.find(s => s.id === +e.target.value);
  try { localStorage.setItem("pm-me", state.me.id); } catch (_) {}
  state.selected = null;
  fillProfile(state.me);
  await loadRecs();
});

/* ---------- discover ---------- */
async function loadRecs(selectId) {
  state.recs = await api(`/api/students/${state.me.id}/recommendations`);
  $("#discover-title").textContent = `Projects for ${state.me.name.split(" ")[0]}`;
  const want = selectId ?? state.selected ?? (matchMedia("(min-width:941px)").matches ? state.recs[0]?.id : null);
  drawList(want);
  if (want) await openProject(want); else drawDetail(null);
}

function drawList(activeId) {
  $("#list").innerHTML = state.recs.map(p => {
    const m = p.match;
    const dim = p.is_member || p.is_full;
    const note = p.is_member ? "You're on this team" : p.is_full ? "Team full" : `${p.open_spots} open ${p.open_spots === 1 ? "spot" : "spots"}`;
    return `<button class="pcard ${dim ? "dim" : ""}" data-id="${p.id}" ${p.id === activeId ? 'aria-current="true"' : ""}>
      <h3>${esc(p.title)}</h3>
      <div class="ring" style="--p:${m.score}"><b>${m.score}%</b></div>
      <div class="meta">${note} · ${p.hours_per_week} hrs/week · ${cap(p.level)}</div>
      <div class="chips">${p.required_skills.slice(0, 6).map(sk => {
        const cls = m.matched_skills.includes(sk) ? "match" : m.related_skills.includes(sk) ? "related" : "";
        return `<span class="chip ${cls}">${esc(sk)}</span>`;
      }).join("")}</div>
    </button>`;
  }).join("") || `<p class="empty">No projects yet. Post the first one.</p>`;
}

$("#list").addEventListener("click", e => {
  const c = e.target.closest(".pcard");
  if (c) openProject(+c.dataset.id);
});

async function openProject(id) {
  state.selected = id;
  $$(".pcard").forEach(c => {
    if (+c.dataset.id === id) c.setAttribute("aria-current", "true"); else c.removeAttribute("aria-current");
  });
  $("#split").classList.add("has-detail");
  const [p, mates] = await Promise.all([
    api(`/api/projects/${id}?student_id=${state.me.id}`),
    api(`/api/projects/${id}/teammates`),
  ]);
  drawDetail(p, mates);
}

function drawDetail(p, mates = []) {
  const el = $("#detail");
  if (!p) { el.innerHTML = `<p class="empty">Pick a project to see who's on the team and which skills are still missing.</p>`; return; }
  const m = p.match, mine = new Set(p.viewer_skills || []);
  const byId = Object.fromEntries(p.members.map(x => [x.id, x]));
  const full = p.open_spots === 0;

  const slots = p.coverage.map(c => {
    if (c.covered_by.length) {
      return `<div class="slot filled"><span>${esc(c.skill)}</span><span class="stack">${c.covered_by.map(id => avatar(byId[id])).join("")}</span></div>`;
    }
    if (mine.has(c.skill) && !p.is_member) {
      return `<div class="slot you"><span>${esc(c.skill)}</span><small>You can fill this</small></div>`;
    }
    return `<div class="slot empty"><span>${esc(c.skill)}</span><small>Still needed</small></div>`;
  }).join("");

  const bar = (label, v) => `<div class="bar"><span>${label}<b>${v}%</b></span><i style="--w:${v}%"></i></div>`;
  const action = p.is_member
    ? (p.members.find(x => x.id === state.me.id)?.role === "Owner"
        ? `<span class="chip tag">You own this project</span>`
        : `<button class="btn" data-act="leave" data-id="${p.id}" data-student="${state.me.id}">Leave team</button>`)
    : full ? `<button class="btn" disabled>Team full</button>`
    : `<button class="btn primary" data-act="join" data-id="${p.id}" data-student="${state.me.id}">Join this team</button>`;

  el.innerHTML = `
    <button class="btn sm back" data-act="back">Back to projects</button>
    <div class="d-head">
      <div>
        <h2>${esc(p.title)}</h2>
        <p class="sub">Led by ${esc(p.owner?.name || "")} · ${p.members.length} of ${p.team_size} members · ${p.hours_per_week} hrs/week · ${cap(p.level)}</p>
        <div class="chips" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">${chips(p.domains, "tag")}</div>
      </div>
      <div class="ring big" style="--p:${m.score}" title="How well this project fits you"><b>${m.score}%</b></div>
    </div>
    <p class="d-desc">${esc(p.description)}</p>
    <div style="margin-top:14px">${action}</div>

    <div class="sec">
      <h3>Why it fits you</h3>
      ${m.reasons.length ? `<ul class="why">${m.reasons.map(r => `<li>${esc(r)}</li>`).join("")}</ul>` : `<p class="hint">Few direct overlaps. It could still be a good place to learn.</p>`}
      <div class="bars">${bar("Skills", m.parts.skills)}${bar("Interests", m.parts.interests)}${bar("Time", m.parts.time)}${bar("Experience", m.parts.experience)}</div>
    </div>

    <div class="sec">
      <h3>Skills covered: ${p.covered_count} of ${p.coverage.length}</h3>
      <p class="hint">Each slot fills when a team member has that skill.</p>
      <div class="board">${slots}</div>
    </div>

    <div class="sec">
      <h3>Team (${p.members.length}/${p.team_size})</h3>
      <div class="people" style="margin-top:8px">${p.members.map(x => `
        <div class="person" style="grid-template-columns:auto 1fr">${avatar(x, "lg")}
          <div><div class="nm">${esc(x.name)} <span class="chip">${esc(x.role)}</span></div>
          <div class="chips">${chips(x.skills.slice(0, 5))}</div></div></div>`).join("")}</div>
    </div>

    <div class="sec">
      <h3>Recommended teammates</h3>
      <p class="hint">Ranked by how many missing skills they bring, plus shared interests and available time.</p>
      ${full ? `<p class="hint">This team is full.</p>` : `<button class="btn" data-act="suggest" data-id="${p.id}">Suggest a balanced team</button>
      <div id="suggest"></div>`}
      <div class="people" style="margin-top:12px">${mates.slice(0, 6).map(s => personRow(s, p, full)).join("")}</div>
    </div>`;
}

function personRow(s, p, full) {
  const f = s.fit;
  return `<div class="person">${avatar(s, "lg")}
    <div><div class="nm">${esc(s.name)}</div>
      <div class="sub">${esc(s.major || "Student")} · ${cap(s.experience)} · ${s.hours_per_week} hrs/week</div>
      <div class="chips">${f.fills.length ? f.fills.map(x => `<span class="chip match">Adds ${esc(x)}</span>`).join("") : `<span class="chip gap">No missing skills covered</span>`}
        ${f.shared_interests.map(x => `<span class="chip tag">${esc(x)}</span>`).join("")}</div></div>
    <div class="sc">${f.score}%<small>team fit</small></div>
    <div class="go"><span class="sub">${f.adds_categories.length ? "Brings " + esc(f.adds_categories.join(", ")) + " to the team" : ""}</span>
      <button class="btn sm primary" data-act="add" data-id="${p.id}" data-student="${s.id}" ${full ? "disabled" : ""}>Add to team</button></div>
  </div>`;
}

/* detail actions */
$("#detail").addEventListener("click", async e => {
  const b = e.target.closest("[data-act]");
  if (!b) return;
  const { act, id, student } = b.dataset;
  try {
    if (act === "back") { $("#split").classList.remove("has-detail"); state.selected = null; return; }
    if (act === "join" || act === "add") {
      const r = await api(`/api/projects/${id}/members`, { method: "POST", body: { student_id: +student } });
      toast(act === "join" ? "You joined the team" : `Added ${r.student} to the team`);
      await loadRecs(+id);
    } else if (act === "leave") {
      await api(`/api/projects/${id}/members/${student}`, { method: "DELETE" });
      toast("You left the team");
      await loadRecs(+id);
    } else if (act === "suggest") {
      const r = await api(`/api/projects/${id}/suggest-team`, { method: "POST" });
      drawSuggestion(r, +id);
    } else if (act === "addall") {
      const ids = JSON.parse(b.dataset.ids);
      for (const sid of ids) await api(`/api/projects/${id}/members`, { method: "POST", body: { student_id: sid } });
      toast(`Added ${ids.length} ${ids.length === 1 ? "person" : "people"} to the team`);
      await loadRecs(+id);
    }
  } catch (err) { toast(err.message); }
});

function drawSuggestion(r, pid) {
  const el = $("#suggest");
  if (!r.team.length) { el.innerHTML = `<div class="suggest"><h3>No one else to add</h3><p class="sub">Nobody available would close a skill gap right now.</p></div>`; return; }
  el.innerHTML = `<div class="suggest">
    <h3>Balanced team: ${r.covered} of ${r.total} skills covered</h3>
    <p class="sub" style="color:var(--muted);font-size:14px">${r.missing.length ? "Still missing: " + esc(r.missing.join(", ")) + ". " : "Every required skill is covered. "}Spans ${esc(r.categories.join(", "))}.</p>
    <div class="people" style="margin:12px 0">${r.team.map(s => `
      <div class="person" style="grid-template-columns:auto 1fr">${avatar(s, "lg")}
      <div><div class="nm">${esc(s.name)}</div><div class="chips">${s.fit.fills.map(x => `<span class="chip match">Adds ${esc(x)}</span>`).join("") || `<span class="chip">Adds variety</span>`}</div></div></div>`).join("")}</div>
    <button class="btn primary" data-act="addall" data-id="${pid}" data-ids='${JSON.stringify(r.team.map(s => s.id))}'>Add all ${r.team.length} to the team</button>
  </div>`;
}

/* ---------- post a project ---------- */
$("#post-form").addEventListener("submit", async e => {
  e.preventDefault();
  const f = e.target, err = $("#post-error");
  err.hidden = true;
  try {
    const p = await api("/api/projects", { method: "POST", body: {
      owner_id: state.me.id, title: f.title.value, description: f.description.value,
      required_skills: postSkills.get(), domains: postDomains.get(),
      team_size: +f.team_size.value, hours_per_week: +f.hours_per_week.value, level: f.level.value } });
    f.reset(); postSkills.set([]); postDomains.set([]);
    toast("Project posted");
    state.selected = null;
    showView("discover");
    await loadRecs(p.id);
  } catch (ex) { err.textContent = ex.message; err.hidden = false; }
});

/* ---------- profile ---------- */
function fillProfile(s) {
  const f = $("#profile-form");
  state.editingId = s ? s.id : null;
  $("#profile-title").textContent = s ? "My profile" : "Create a profile";
  $("#profile-save").textContent = s ? "Save changes" : "Create profile";
  $("#profile-new").textContent = s ? "Create a new profile" : "Cancel";
  const v = s || { name: "", email: "", major: "", year: "", bio: "", skills: [], interests: [], experience: "beginner", hours_per_week: 6 };
  ["name", "email", "major", "year", "bio", "experience", "hours_per_week"].forEach(k => f[k].value = v[k]);
  profSkills.set(v.skills);
  profInterests.set(v.interests);
  $("#profile-error").hidden = true;
}
$("#profile-new").addEventListener("click", () => fillProfile(state.editingId ? null : state.me));

$("#profile-form").addEventListener("submit", async e => {
  e.preventDefault();
  const f = e.target, err = $("#profile-error");
  err.hidden = true;
  const body = { name: f.name.value, email: f.email.value, major: f.major.value, year: f.year.value, bio: f.bio.value,
    skills: profSkills.get(), interests: profInterests.get(), experience: f.experience.value, hours_per_week: +f.hours_per_week.value };
  try {
    const creating = !state.editingId;
    const saved = creating ? await api("/api/students", { method: "POST", body })
                           : await api(`/api/students/${state.editingId}`, { method: "PUT", body });
    state.students = await api("/api/students");
    state.me = state.students.find(s => s.id === saved.id);
    try { localStorage.setItem("pm-me", saved.id); } catch (_) {}
    drawWho();
    toast(creating ? "Profile created" : "Profile saved");
    state.selected = null;
    showView("discover");
    await loadRecs();
  } catch (ex) { err.textContent = ex.message; err.hidden = false; }
});

boot().catch(err => { $("#list").innerHTML = `<p class="empty">Couldn't load ProjectMatch: ${esc(err.message)}</p>`; });
