/* ══════════════════════════════════════════════════════════
   DUNE: Imperium Uprising — frontend v2
   ══════════════════════════════════════════════════════════ */

// ─────────────── global state ───────────────
const G = {
  state: null,
  selectedCard: null,   // {id, validLocations:[str]}
  pendingChoice: null,
  playerColors: ["p0","p1","p2","p3"],
  playerCount: 3,
  humanId: null,
  selectedLeader: null,
  leaders: [],
  objective: null,
  conflictHistory: [],
};

// ─────────────── startup ────────────────────
(async function loadLeaders() {
  const data = await api("GET", "/api/leaders");
  if (!data) return;
  G.leaders = Array.isArray(data) ? data : [];
  renderLeaderPicker();
})();

function renderLeaderPicker() {
  const el_ = document.getElementById("leader-picker");
  el_.innerHTML = "";
  if (!G.leaders.length) { el_.innerHTML = '<span class="leader-loading">No leaders available</span>'; return; }
  G.leaders.forEach(l => {
    const btn = el("button","leader-btn");
    btn.textContent = l.name;
    btn.dataset.id = l.id;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".leader-btn").forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      G.selectedLeader = l.id;
    });
    el_.appendChild(btn);
  });
  // auto-select first
  if (G.leaders.length) {
    el_.firstChild.classList.add("selected");
    G.selectedLeader = G.leaders[0].id;
  }
}

// ─────────────── setup screen ───────────────
document.querySelectorAll(".count-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".count-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    G.playerCount = parseInt(btn.dataset.count);
  });
});

document.getElementById("start-btn").addEventListener("click", async () => {
  const name = document.getElementById("setup-name").value.trim() || "Player";
  const snap = await api("POST", "/api/new-game", {
    player_count: G.playerCount,
    human_name: name,
    selected_leader: G.selectedLeader,
  });
  if (snap) {
    G.humanId = snap.state.viewer_player_id;
    document.getElementById("setup-overlay").classList.add("hidden");
    document.getElementById("game").classList.remove("hidden");
    applySnapshot(snap);
    // Show objective card
    const human = snap.state.players.find(p => p.player_id === G.humanId);
    if (human?.objective) {
      G.objective = human.objective;
      showObjective();
    }
  }
});

// ─────────────── keyboard shortcuts ─────────
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  const phase = G.state?.available_actions?.phase;
  if (e.key === "r" || e.key === "R") {
    if (phase === "agent_turn") { e.preventDefault(); doReveal(); }
  } else if (e.key === "d" || e.key === "D") {
    if (phase === "acquisition") { e.preventDefault(); endAcquisition(); }
  } else if (e.key === "c" || e.key === "C") {
    if (phase === "combat") { e.preventDefault(); endCombat(); }
  } else if (e.key === "Escape") {
    clearSelectedCard();
  }
});

// ─────────────── objective modal ────────────
function showObjective() {
  if (!G.objective) return;
  const modal = document.getElementById("objective-modal");
  const content = document.getElementById("objective-content");
  content.innerHTML = `
    <div class="objective-name">🎯 ${G.objective.name || "Unknown"}</div>
    <div class="objective-desc">${G.objective.description || G.objective.tag || ""}</div>
  `;
  modal.classList.remove("hidden");
}
function closeObjective() {
  document.getElementById("objective-modal").classList.add("hidden");
}

// ─────────────── leader modal ───────────────
function showLeader() {
  const human = G.state?.players?.find(p => p.player_id === G.state.viewer_player_id);
  const leader = human?.leader;
  if (!leader) return;

  document.getElementById("leader-title").textContent = `👑 ${leader.name || "Your Leader"}`;
  const content = document.getElementById("leader-content");

  // ── Signet ability (current effects for the leader's training-track level) ──
  const signetFx = leader.signet_effects && leader.signet_effects.length
    ? leader.signet_effects
    : (Array.isArray(leader.signet) ? leader.signet : []);
  const signetHTML = leaderEffectsHTML(signetFx,
    "No signet effect at your current training-track position.");

  // ── Passive ability ──
  const passive = leader.passive;
  let passiveHTML;
  if (passive) {
    const pName = passive.name ? `<div class="leader-ability-name">${passive.name}</div>` : "";
    const when  = passive.phase ? `<span class="leader-when">Triggers: ${_cap(passive.phase)} phase</span>` : "";
    const desc  = passive.description ? `<div class="leader-desc">${passive.description}</div>` : "";
    const cost  = _asArr(passive.cost);
    const rew   = _asArr(passive.reward);
    let effLine = "";
    if (cost.length || rew.length) {
      const costTxt = cost.map(x => describeEffectText(x, true)).filter(Boolean).join(", ");
      const rewTxt  = rew.map(x => describeEffectText(x)).filter(Boolean).join(", ");
      effLine = `<div class="leader-eff">${costTxt ? `${costTxt} → ` : ""}${rewTxt || ""}</div>`;
    }
    passiveHTML = `${pName}${desc}${effLine}${when}`;
    if (!passiveHTML.trim()) passiveHTML = `<div class="leader-empty">See card.</div>`;
  } else {
    passiveHTML = `<div class="leader-empty">This leader has no passive ability.</div>`;
  }

  content.innerHTML = `
    <div class="leader-section">
      <div class="leader-section-title">💍 Signet Ring Ability</div>
      <div class="leader-hint">Triggered when you play the <b>Signet Ring</b> card.</div>
      ${signetHTML}
    </div>
    <div class="leader-section">
      <div class="leader-section-title">✦ Passive Ability</div>
      ${passiveHTML}
    </div>
  `;
  document.getElementById("leader-modal").classList.remove("hidden");
}

function closeLeader() {
  document.getElementById("leader-modal").classList.add("hidden");
}

/** Render a list of leader effects as readable lines, expanding choices into OR rows. */
function leaderEffectsHTML(effects, emptyMsg) {
  const arr = _asArr(effects);
  if (!arr.length) return `<div class="leader-empty">${emptyMsg || "—"}</div>`;
  const rows = [];
  arr.forEach(e => {
    if (e && e.type === "choice") {
      const opts = (e.options || []).map(o => `<div class="leader-eff">${describeOptionText(o)}</div>`);
      rows.push(`<div class="leader-eff-choice">Choose one:</div>` + opts.join(`<div class="leader-or">— OR —</div>`));
    } else if (e && (e.type === "conditional_multi" || e.type === "conditional_bonuses")) {
      const opts = (e.options || []).map(o => `<div class="leader-eff">${o.description || describeOptionText(o)}</div>`);
      rows.push(opts.join(""));
    } else {
      rows.push(`<div class="leader-eff">${describeEffectText(e)}</div>`);
    }
  });
  return rows.join("");
}

// ─────────────── api helpers ────────────────
async function api(method, url, body) {
  try {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(url, opts);
    const data = await r.json();
    if (!r.ok) { showError(data.detail || "Request failed"); return null; }
    return data;
  } catch(e) { showError(e.message); return null; }
}

async function postAction(actionDict) {
  const snap = await api("POST", "/api/action", actionDict);
  if (snap) applySnapshot(snap);
}

// ─────────────── main render ────────────────
function applySnapshot(snap) {
  G.state = snap.state;
  G.pendingChoice = snap.pending_choice;
  G.pendingTroopDeployment = snap.pending_troop_deployment || null;
  G.conflictHistory = snap.conflict_history || [];
  const evts = snap.events || [];
  appendEvents(evts);
  render();
  if (G.pendingChoice) showChoiceModal(G.pendingChoice);
  else if (G.pendingTroopDeployment) showTroopPicker(G.pendingTroopDeployment);
  // Check for combat events to show toast
  const combatEv = evts.find(e => e.type === "combat_resolved");
  if (combatEv) showCombatToast(combatEv);
  // Show game-over overlay
  if (G.state?.game_over) showGameOver(G.state.game_over_data);
}

function render() {
  const s = G.state;
  if (!s) return;
  G.spyMap = buildSpyMap(s);
  renderTopBar(s);
  renderContractDisplay(s);
  renderFactionSpaces(s);
  renderNeutralSpaces(s);
  renderCombatZone(s);
  renderImperiumRow(s);
  renderPlayerArea(s);
  updateActionButtons(s);
  renderActionHint(s);
  updatePhaseStyling(s);
}

// Build lookup: space name → { postId, postName, ownerIdx (null if empty) }
function buildSpyMap(s) {
  const map = {};
  const posts = s.board?.observation_posts || [];
  const spyOwners = {};
  s.players.forEach((p, idx) => {
    (p.spies_placed || []).forEach(pid => { spyOwners[String(pid)] = idx; });
  });
  posts.forEach(post => {
    const ownerIdx = spyOwners[String(post.id)] !== undefined ? spyOwners[String(post.id)] : null;
    (post.connected_locations || []).forEach(name => {
      map[name] = { postId: post.id, postName: post.name, ownerIdx };
    });
  });
  return map;
}

// ─────────────── TOP BAR ────────────────────
function renderTopBar(s) {
  document.getElementById("round-label").textContent = `Round ${s.round}`;
  document.getElementById("phase-badge").textContent = phaseLabel(s.available_actions?.phase || s.phase, s.available_actions?.underlying_phase);

  const bar = document.getElementById("opponents-bar");
  bar.innerHTML = "";
  s.players.forEach((p, i) => {
    if (p.player_id === s.viewer_player_id) return;
    const chip = el("div","opponent-chip");
    const leaderName = p.leader?.name ? ` (${p.leader.name})` : "";
    const firstMark = i === s.first_player_index ? `<span class="first-player-badge" title="First player this round">1st</span>` : "";
    chip.innerHTML = `
      <span class="chip-color" style="background:var(--${G.playerColors[i]})"></span>
      ${firstMark}
      <span>${shortName(p.name)}${leaderName}</span>
      <span class="chip-vp">⭐${p.victory_points}</span>
      <span class="chip-sol" style="color:var(--solari)">●${p.solari}</span>
      <span class="chip-spi" style="color:var(--spice)">◆${p.spice}</span>
      <span style="color:var(--text-dim)">🃏${p.hand_size}</span>
    `;
    bar.appendChild(chip);
  });
}

function phaseLabel(phase, underlying) {
  const map = {
    agent_turn:"Agent Phase", acquisition:"Acquisition", player_turns:"Playing",
    combat:"⚔ Combat", recall:"Recall", game_over:"GAME OVER",
    choice:"Choose…",
  };
  if (phase === "choice" && underlying) return (map[underlying] || underlying) + " — Choose";
  return map[phase] || phase || "—";
}

// ─────────────── CONTRACT DISPLAY (board Trade panel) ────────────
function renderContractDisplay(s) {
  const panel = document.getElementById("contract-display");
  if (!panel) return;
  panel.innerHTML = "";
  const aa = s.available_actions || {};
  const inAcq = aa.phase === "acquisition";
  const canAccept = inAcq && aa.can_accept_contract;
  const contracts = s.board?.contract_row || [];

  if (!contracts.length) {
    const empty = el("div",""); empty.style.cssText = "font-size:8px;color:var(--text-dim)";
    empty.textContent = "None available";
    panel.appendChild(empty);
    return;
  }

  contracts.forEach(c => {
    const itemClass = "contract-item" + (canAccept ? " contract-takeable" : "");
    const item = el("div", itemClass);
    const hint = canAccept ? ' <span class="ci-take-hint">click to take</span>' : "";
    item.innerHTML = `
      <div class="ci-name">${c.name}${hint}</div>
      <div class="ci-cond">${contractCondition(c)}</div>
      <div class="ci-reward">→ ${formatRewardsText(c.rewards || [])}</div>
    `;
    if (canAccept) item.addEventListener("click", () => promptAcceptContract(c));
    panel.appendChild(item);
  });
}

function contractCondition(c) {
  if (c.completion_type === "immediate") return "immediate";
  if (c.completion_type === "location")  return `visit: ${c.completion_target}`;
  if (c.completion_type === "harvest")   return `harvest ≥${c.required_spice} spice`;
  if (c.completion_type === "acquire_card") return `buy a card`;
  return c.completion_type || "";
}

// ─────────────── FACTION SPACES ─────────────
function renderFactionSpaces(s) {
  const factions = ["fremen","bene_gesserit","spacing_guild","emperor"];
  factions.forEach(f => {
    const infEl = document.getElementById(`inf-${f}`);
    if (infEl) renderInfluenceCol(infEl, f, s);

    const cont = document.getElementById(`spaces-${f}`);
    if (!cont) return;
    cont.innerHTML = "";
    const spaces = (s.board?.spaces || []).filter(sp => normFaction(sp.faction) === f);
    spaces.forEach(sp => {
      const node = renderBoardSpace(sp, s, G.spyMap[sp.name]);
      node.classList.add(`space-${f}`);
      cont.appendChild(node);
    });
  });
}

function normFaction(f) {
  if (!f) return null;
  return f.toLowerCase().replace(/ /g,"_").replace("benegesserit","bene_gesserit").replace("spacingguild","spacing_guild");
}

function renderInfluenceCol(colEl, faction, s) {
  colEl.innerHTML = "";
  s.players.forEach((p, idx) => {
    const level = p.influence?.[faction] ?? 0;
    const alliance = p.alliances?.[faction] ?? false;
    const row = el("div","inf-row");

    const letter = el("span","inf-letter");
    letter.textContent = p.name[0];
    letter.style.color = `var(--${G.playerColors[idx]})`;
    row.appendChild(letter);

    const pips = el("span","inf-pips");
    for (let i = 0; i < 4; i++) {
      const pip = el("span","inf-pip" + (i < level ? " filled" : ""));
      if (i < level) pip.style.background = `var(--${G.playerColors[idx]})`;
      pips.appendChild(pip);
    }
    row.appendChild(pips);

    if (alliance) {
      const star = el("span","alliance-star"); star.textContent = "★";
      row.appendChild(star);
    }
    colEl.appendChild(row);
  });
}

// ─────────────── NEUTRAL SPACES ─────────────
function renderNeutralSpaces(s) {
  const landsraadEl  = document.getElementById("spaces-landsraad");
  const shippingEl   = document.getElementById("spaces-shipping");
  const cityEl       = document.getElementById("spaces-city");
  const desertEl     = document.getElementById("spaces-desert");

  landsraadEl.innerHTML = "";
  shippingEl.innerHTML  = "";
  cityEl.innerHTML      = "";
  desertEl.innerHTML    = "";

  const neutral = (s.board?.spaces || []).filter(sp => !normFaction(sp.faction));
  neutral.forEach(sp => {
    const icon = sp.agent_icon?.toLowerCase() || "";
    const name = sp.name?.toLowerCase() || "";
    const node = renderBoardSpace(sp, s, G.spyMap[sp.name]);

    if (icon === "green") {
      node.classList.add("space-landsraad");
      landsraadEl.appendChild(node);
    } else if (name.includes("shipping") || name.includes("accept")) {
      node.classList.add("space-trade");
      shippingEl.appendChild(node);
    } else if (icon === "yellow") {
      node.classList.add("space-desert");
      desertEl.appendChild(node);
    } else {
      node.classList.add("space-city");
      cityEl.appendChild(node);
    }
  });
}

// ─────────────── BOARD SPACE ────────────────
function renderBoardSpace(sp, s, spyInfo) {
  const div = el("div","board-space");

  const isValid = G.selectedCard && G.selectedCard.validLocations.includes(String(sp.id));
  if (isValid) div.classList.add("valid-target");
  if (sp.occupied_by) div.classList.add("occupied");

  // Header: name + spy dot + cost badge
  const hdr = el("div","sp-header");
  const nameEl = el("span","sp-name"); nameEl.textContent = sp.name;
  hdr.appendChild(nameEl);

  // Spy observation dot
  if (spyInfo) {
    const dot = el("div","spy-dot");
    if (spyInfo.ownerIdx !== null) {
      dot.classList.add("spy-occupied");
      dot.style.background = `var(--${G.playerColors[spyInfo.ownerIdx]})`;
      const ownerName = s.players[spyInfo.ownerIdx]?.name || "?";
      const isHuman = s.players[spyInfo.ownerIdx]?.player_id === s.viewer_player_id;
      dot.title = `🕵 ${spyInfo.postName} — ${isHuman ? "your spy" : ownerName}`;
    } else {
      dot.title = `Observation post: ${spyInfo.postName}`;
    }
    hdr.appendChild(dot);
  }

  const costArr = sp.cost || [];
  if (costArr.length) {
    const costEl = el("span","sp-cost-badge");
    costEl.innerHTML = costArr.map(c => {
      const amt = c.amount || 1;
      const res = c.resource || "";
      return `${amt}${resourceIconHTML(res)}`;
    }).join("");
    hdr.appendChild(costEl);
  }
  div.appendChild(hdr);

  // Rewards — choice effects expand into OR rows; regular effects are one row
  const rwArr = sp.reward || [];
  if (rwArr.length) {
    const rwDiv = el("div","sp-rewards");
    const nonChoice = rwArr.filter(e => e.type !== "choice");
    const choices   = rwArr.filter(e => e.type === "choice");

    if (nonChoice.length) {
      const row = el("div","sp-reward-row");
      nonChoice.forEach(e => { const s2 = el("span",""); s2.innerHTML = describeEffectHTML(e); row.appendChild(s2); });
      rwDiv.appendChild(row);
    }
    choices.forEach(ce => {
      (ce.options || []).forEach((opt, idx) => {
        if (idx > 0) { const or = el("div","sp-or"); or.textContent = "OR"; rwDiv.appendChild(or); }
        const row = el("div","sp-choice-option");
        row.innerHTML = formatOptionRewardsHTML(opt);
        rwDiv.appendChild(row);
      });
    });
    div.appendChild(rwDiv);
  }

  // Influence/alliance requirements
  const checks = sp.check || [];
  if (checks.length) {
    const req = el("div","sp-checks");
    const factionIcons = {fremen:"🌵",bene_gesserit:"🔮",spacing_guild:"🚀",emperor:"👑"};
    checks.forEach(c => {
      const t = c.type || "";
      if (t === "influence") {
        const ico = el("span","sp-check-inf");
        const fIcon = factionIcons[c.target] || "★";
        ico.textContent = `${c.amount||1}+ ${fIcon}`;
        req.appendChild(ico);
      } else if (t === "council_seat") {
        const ico = el("span","sp-check-inf"); ico.textContent = "🪑";
        req.appendChild(ico);
      } else if (t === "alliance") {
        const ico = el("span","sp-check-inf");
        const fIcon = factionIcons[c.target] || "★";
        ico.textContent = `★${fIcon}`;
        req.appendChild(ico);
      }
    });
    if (req.children.length) div.appendChild(req);
  }

  // Combat marker — readable badge in the corner
  if (sp.is_combat_space) {
    const marker = el("span","sp-combat-badge");
    marker.innerHTML = "⚔ COMBAT";
    marker.title = "Deploy troops here to fight in the Conflict";
    div.classList.add("is-combat-space");
    div.appendChild(marker);
  }

  // Spice bonus (accumulated on maker spaces)
  if (sp.spice_bonus > 0) {
    const bonus = el("div","sp-spice-bonus");
    bonus.innerHTML = `+${sp.spice_bonus}<i class="efx spice"></i>`;
    div.appendChild(bonus);
  }

  // Occupant
  if (sp.occupied_by) {
    const pidx = s.players.findIndex(p => p.player_id === sp.occupied_by);
    const pobj = s.players[pidx];
    const name = pobj?.name || "?";
    const occ = el("div", `sp-occupant occ-${Math.max(pidx,0)}`);
    occ.textContent = pobj?.is_human ? `YOU` : `BOT-${name[0]}`;
    div.appendChild(occ);
  }

  div.addEventListener("click", () => {
    if (G.selectedCard && isValid) placeAgent(G.selectedCard.id, sp.id, sp.is_combat_space);
  });
  return div;
}

function agentIconLabel(icon) {
  const map = { fremen:"🌵", bene_gesserit:"🔮", spacing_guild:"🚀", emperor:"👑", yellow:"◆", blue:"🏙", green:"🏛", spy:"🕵", city:"🏙" };
  return map[icon?.toLowerCase()] || icon || "◦";
}

// ─────────────── COMBAT ZONE ────────────────
function renderCombatZone(s) {
  const conflict = s.board?.current_conflict;
  const cfEl = document.getElementById("current-conflict");
  if (conflict) {
    cfEl.innerHTML = `
      <div class="cf-name">⚔ ${conflict.name}</div>
      <div class="cf-lvl">Lvl ${conflict.level}</div>
      <div class="cf-reward">${renderConflictRewards(conflict.rewards)}</div>
    `;
  } else {
    cfEl.innerHTML = `<div style="color:var(--text-dim);font-size:8px">No conflict</div>`;
  }

  const cpDiv = document.getElementById("combat-players");
  cpDiv.innerHTML = "";
  s.players.forEach((p, i) => {
    const row = el("div","combat-player-row");
    const str = p.combat_strength || 0;
    const swords = p.temp_swords || 0;
    const parts = [`${p.troops_in_conflict}🗡`];
    if (p.sandworms_in_conflict > 0) parts.push(`+${p.sandworms_in_conflict}🪱`);
    if (swords > 0) parts.push(`+${swords}⚔`);
    row.innerHTML = `
      <span class="cp-color" style="background:var(--${G.playerColors[i]})"></span>
      <span class="cp-info">${shortName(p.name)} — ${parts.join("")}</span>
      <span class="cp-str">${str}</span>
    `;
    cpDiv.appendChild(row);
  });

  const garr = document.getElementById("garrisons");
  garr.innerHTML = s.players.map((p,i) =>
    `<span class="garrison-chip" style="color:var(--${G.playerColors[i]})">${p.name[0]}:${p.troops_in_garrison}</span>`
  ).join(" ");

  // ── Conflict history ──
  renderConflictHistory();
}

function renderConflictHistory() {
  const hist = G.conflictHistory || [];
  const garr = document.getElementById("garrisons");
  if (!garr) return;

  // Remove and re-create history elements each render to keep them fresh
  const existing = document.getElementById("cf-hist-toggle");
  if (existing) existing.remove();
  const existingPanel = document.getElementById("cf-hist-panel");
  if (existingPanel) existingPanel.remove();

  if (!hist.length) return;

  const histPanel = el("div","cf-hist-panel hidden");
  histPanel.id = "cf-hist-panel";
  [...hist].reverse().forEach(h => {
    const row = el("div","cf-hist-row");
    const wormNote = h.worm_players?.length ? ` 🪱×2` : "";
    const winnerStr = h.tied ? "🤝 Tied" : `🏆 ${h.winner}`;
    row.innerHTML = `
      <span class="ch-round">R${h.round}</span>
      <span class="ch-name">${h.name}</span>
      <span class="ch-winner">${winnerStr}${wormNote}</span>
    `;
    histPanel.appendChild(row);
  });

  const histToggle = el("button","cf-hist-toggle");
  histToggle.id = "cf-hist-toggle";
  histToggle.textContent = `📜 ${hist.length} past conflict${hist.length > 1 ? "s" : ""}`;
  histToggle.addEventListener("click", () => histPanel.classList.toggle("hidden"));

  // Insert after garrisons
  garr.after(histToggle, histPanel);
}

function renderConflictRewards(rewards) {
  if (!rewards) return "";
  return Object.entries(rewards).map(([rank, effects]) => {
    const rankLabel = rank === "1" ? "🥇" : rank === "2" ? "🥈" : "🥉";
    return `${rankLabel}${formatRewardsText(effects)}`;
  }).join(" ");
}

// ─────────────── IMPERIUM ROW ───────────────
function renderImperiumRow(s) {
  const aa = s.available_actions || {};
  const inAcq = aa.phase === "acquisition";
  const persuasion = aa.persuasion_left || 0;

  const rowEl = document.getElementById("imperium-row");
  rowEl.innerHTML = "";
  (s.board?.imperium_row || []).forEach(c => {
    const div = buildCard(c, "row-card", inAcq, persuasion);
    if (inAcq) div.addEventListener("click", () => tryAcquireCard(c, "row"));
    rowEl.appendChild(div);
  });

  const resEl = document.getElementById("reserve-piles");
  resEl.innerHTML = "";
  const rp = aa.reserve_prepare || s.board?.reserve_prepare_the_way;
  const rs = aa.reserve_spice   || s.board?.reserve_spice_must_flow;
  [[rp, "prepare"], [rs, "spice"]].forEach(([pile, src]) => {
    if (!pile) return;
    const card = pile.card || pile.top;
    if (!card) return;
    const rem  = pile.remaining || 0;
    const div = buildCard(card, "row-card", inAcq, persuasion);
    const extra = el("div",""); extra.textContent = `×${rem} left`; extra.style.cssText="font-size:8px;color:var(--text-dim);padding:2px 6px";
    div.appendChild(extra);
    if (inAcq) div.addEventListener("click", () => tryAcquireCard(card, src));
    resEl.appendChild(div);
  });
}

// ─────────────── PLAYER AREA ────────────────
function renderPlayerArea(s) {
  const human = s.players.find(p => p.player_id === s.viewer_player_id);
  if (!human) return;
  const aa = s.available_actions || {};
  const inAcq = aa.phase === "acquisition";
  const persuasion = aa.persuasion_left || 0;

  const leaderStr = human.leader?.name ? ` · ${human.leader.name}` : "";
  const humanIdx = s.players.findIndex(p => p.player_id === s.viewer_player_id);
  const firstStr = humanIdx === s.first_player_index ? " 🥇1st" : "";
  document.getElementById("your-name-label").textContent = (human.name || "").toUpperCase() + leaderStr + firstStr;

  // Resources bar
  const resBar = document.getElementById("player-resources");
  if (resBar) {
    const aa2 = s.available_actions || {};
    const agentsStr = `${human.agents_available}/${human.total_available_agents}`;
    const vpTip = vpBreakdownText(human);
    resBar.innerHTML = `
      <span class="res-chip res-vp" title="${vpTip}"><i class="efx vp">⭐</i><span class="rc-val">${human.victory_points}</span><span class="rc-lbl">VP</span></span>
      <span class="res-chip res-sol"  title="Solari"><i class="efx solari"></i><span class="rc-val">${human.solari}</span><span class="rc-lbl">Sol</span></span>
      <span class="res-chip res-spi"  title="Spice"><i class="efx spice"></i><span class="rc-val">${human.spice}</span><span class="rc-lbl">Spice</span></span>
      <span class="res-chip res-wat"  title="Water">💧<span class="rc-val">${human.water}</span><span class="rc-lbl">Water</span></span>
      <span class="res-chip res-trp"  title="Troops in garrison">🗡<span class="rc-val">${human.troops_in_garrison}</span><span class="rc-lbl">Troops</span></span>
      <span class="res-chip res-agt"  title="Agents available">📍<span class="rc-val">${agentsStr}</span><span class="rc-lbl">Agents</span></span>
    `;
  }

  const pbadge = document.getElementById("persuasion-display");
  if (inAcq) {
    pbadge.classList.remove("hidden");
    pbadge.textContent = `${persuasion} persuasion`;
    pbadge.style.opacity = persuasion > 0 ? "1" : "0.5";
  } else {
    pbadge.classList.add("hidden");
  }

  // Hand
  const handEl = document.getElementById("hand-cards");
  handEl.innerHTML = "";
  (human.hand || []).forEach(c => {
    const div = buildCard(c, "hand-card", false, 0);
    if (aa.phase === "agent_turn") {
      const entry = (aa.playable_cards || []).find(e => e.card_id === c.id);
      if (entry && entry.valid_location_ids.length > 0) {
        div.classList.add("selectable");
        if (G.selectedCard?.id === c.id) div.classList.add("card-selected");
        div.addEventListener("click", () => selectCard(c, entry.valid_location_ids));
      } else {
        // No valid agent locations — check if it's a reveal-only card
        const isRevealOnly = !c.agent_icons?.length && c.reveal_effects?.length > 0;
        if (isRevealOnly) {
          div.classList.add("reveal-only");
          const tag = el("div","reveal-only-tag"); tag.textContent = "REVEAL";
          div.appendChild(tag);
        } else {
          div.style.opacity = ".45";
        }
      }
    } else if (inAcq) {
      // In acquisition phase, hand is revealed but not clickable for placement
      div.style.opacity = ".6";
    }
    handEl.appendChild(div);
  });

  document.getElementById("intrigue-count").textContent = human.intrigue_count || 0;

  const intEl = document.getElementById("intrigue-cards");
  intEl.innerHTML = "";
  (human.intrigue_cards || []).forEach(c => {
    const div = buildIntrigueCard(c, aa.phase);
    intEl.appendChild(div);
  });

  // Active contracts
  const acEl = document.getElementById("active-contracts");
  acEl.innerHTML = "";
  (human.contracts_active || []).forEach(c => {
    const chip = el("div","active-contract-chip");
    chip.innerHTML = `<div class="ac-name">${c.name}</div><div class="ac-cond">${contractCondition(c)}</div>`;
    acEl.appendChild(chip);
  });

  // Discard piles
  const discardStrip = document.getElementById("discard-piles-strip");
  discardStrip.innerHTML = "";
  s.players.forEach((p, i) => {
    if (!p.discard_size) return;
    const btn = el("button","discard-pile-btn");
    btn.textContent = `${p.name[0]} (${p.discard_size})`;
    btn.style.borderColor = `var(--${G.playerColors[i]})`;
    btn.addEventListener("click", () => showDiscard(p, s));
    discardStrip.appendChild(btn);
  });
}

// ─────────────── ACTION BUTTONS ─────────────
function updateActionButtons(s) {
  const aa = s.available_actions || {};
  // When a choice is pending, keep the button for the underlying phase visible
  // (it's blocked by the execute_action guard anyway, but gives context)
  const effectivePhase = (aa.phase === "choice" && aa.underlying_phase) ? aa.underlying_phase : aa.phase;
  document.getElementById("reveal-btn").classList.toggle("hidden", effectivePhase !== "agent_turn");
  document.getElementById("end-acq-btn").classList.toggle("hidden", effectivePhase !== "acquisition");
  document.getElementById("end-combat-btn").classList.toggle("hidden", effectivePhase !== "combat");
}

function doReveal() { postAction({ type: "reveal" }); clearSelectedCard(); }
function endAcquisition() { postAction({ type: "end_acquisition" }); }
function endCombat() { postAction({ type: "end_combat" }); }

// ─────────────── ACTION HINT ─────────────
function renderActionHint(s) {
  const el_ = document.getElementById("action-hint");
  if (!el_) return;
  const aa = s.available_actions || {};
  const phase = aa.phase || s.phase;
  const effectivePhase = (phase === "choice" && aa.underlying_phase) ? aa.underlying_phase : phase;

  let hint = "";
  if (effectivePhase === "agent_turn") {
    const playable = aa.playable_cards || [];
    const hasSelectable = playable.some(e => e.valid_location_ids?.length > 0);
    if (G.selectedCard) {
      hint = "Click a <span class='hint-green'>green space</span> to send your agent there";
    } else if (hasSelectable) {
      hint = "Select a card from your hand, then click a <span class='hint-green'>green space</span>";
    } else {
      hint = "No agent spots available — press <kbd>R</kbd> to reveal your hand";
    }
  } else if (effectivePhase === "acquisition") {
    const pts = aa.persuasion_left || 0;
    hint = pts > 0
      ? `Spend your <span class='hint-gold'>${pts} persuasion</span> on Imperium Row cards, then press <kbd>D</kbd>`
      : `No persuasion left — press <kbd>D</kbd> to end your turn`;
  } else if (effectivePhase === "combat") {
    const n = (aa.combat_intrigue_ids || []).length;
    hint = n > 0
      ? `Play your <span class='hint-gold'>${n} combat intrigue${n>1?"s":""}</span> if you wish, then press <kbd>C</kbd> to resolve the conflict`
      : `Press <kbd>C</kbd> to resolve the conflict`;
  } else if (phase === "choice") {
    hint = "Make a choice above ↑";
  }
  el_.innerHTML = hint;
  el_.style.display = hint ? "" : "none";
}

// ─────────────── PHASE STYLING ───────────
function updatePhaseStyling(s) {
  const aa = s.available_actions || {};
  const phase = aa.phase || s.phase;
  const badge = document.getElementById("phase-badge");
  const playerArea = document.querySelector(".player-area");

  // Color the phase badge and player area glow by phase
  badge.className = "phase-badge phase-" + (phase || "other");
  const isMyTurn = phase === "agent_turn" || phase === "acquisition";
  playerArea?.classList.toggle("player-turn-active", isMyTurn);
}

// ─────────────── CARD SELECTION / PLACEMENT ─────────────
function selectCard(card, validLocations) {
  if (G.selectedCard?.id === card.id) { clearSelectedCard(); return; }
  G.selectedCard = { id: card.id, validLocations };
  render();
}
function clearSelectedCard() { G.selectedCard = null; render(); }

function placeAgent(cardId, locationId, isCombatSpace) {
  // Always place with troops=0. Location rewards (e.g. Arrakeen +1 troop)
  // are applied first; if the space is combat and troops remain in garrison,
  // the server returns pending_troop_deployment and the picker opens.
  postAction({ type: "place_agent", card_id: cardId, location_id: String(locationId) });
  clearSelectedCard();
}

function showTroopPicker(p) {
  // p = { location_name, max_troops, bonus }
  const modal = document.getElementById("choice-modal");
  document.getElementById("choice-title").textContent = `Deploy Troops to Conflict (${p.location_name})?`;
  const bonusNote = p.bonus > 0 ? ` (includes +${p.bonus} bonus from ${p.location_name})` : "";
  document.getElementById("choice-desc").textContent =
    `Send up to ${p.max_troops} troops from garrison to the conflict${bonusNote}.`;
  const optEl = document.getElementById("choice-options");
  optEl.innerHTML = "";
  for (let t = 0; t <= p.max_troops; t++) {
    const btn = el("button","choice-btn");
    btn.textContent = t === 0 ? "No troops" : `${t} troop${t > 1 ? "s" : ""}`;
    btn.addEventListener("click", () => {
      modal.classList.add("hidden");
      postAction({ type: "deploy_troops", troops: t });
    });
    optEl.appendChild(btn);
  }
  modal.classList.remove("hidden");
}

function tryAcquireCard(card, source) {
  const aa = G.state?.available_actions || {};
  if (aa.phase !== "acquisition") return;
  if (card.cost > aa.persuasion_left) {
    showError(`Not enough persuasion (have ${aa.persuasion_left}, need ${card.cost})`); return;
  }
  postAction({ type: "acquire_card", card_id: card.id, source });
}

function promptAcceptContract(contract) {
  postAction({ type: "acquire_contract", contract_id: String(contract.id) });
}

// ─────────────── CHOICE MODAL ───────────────
function showChoiceModal(choice) {
  const modal = document.getElementById("choice-modal");
  document.getElementById("choice-title").textContent = choiceTitle(choice.type);
  document.getElementById("choice-desc").textContent  = choice.description || "";
  const optEl = document.getElementById("choice-options");
  optEl.innerHTML = "";
  getChoiceItems(choice).forEach(item => {
    const btn = el("button","choice-btn"+(item.disabled?" disabled":""));
    btn.textContent = item.label;
    if (!item.disabled) btn.addEventListener("click", () => {
      modal.classList.add("hidden");
      postAction({ type:"resolve_choice", option_id: item.value });
    });
    optEl.appendChild(btn);
  });
  modal.classList.remove("hidden");
}

function choiceTitle(ctype) {
  const map = {
    choice:"Choose an option", spy_post:"Place Spy", play_spy:"Play Spy",
    influence_faction:"Choose Faction", conditional:"Pay for Bonus?",
    trash_card:"Trash a Card", trash_to_acquire:"Trash to Acquire",
    discard_card:"Discard a Card", steal_intrigue:"Steal Intrigue From",
    recall_agent:"Recall Agent From", accept_contract:"Accept a Contract",
    acquire_card:"Acquire Card (Free)", choose_opponent_discard:"Force Discard",
    play_spy_on_space:"Plant Spy", conditional_multi_choice:"Optional Bonuses",
    reveal_passive_choice:"Leader Passive",
  };
  return map[ctype] || "Make a Choice";
}

function getChoiceItems(choice) {
  const ctype = choice.type;
  if (ctype === "choice") return (choice.options||[]).map(o => {
    const rw = _rewardOf(o);
    const cost = _costOf(o);
    let label;
    if (rw.length) {
      const rwStr = formatRewardsText(rw);
      label = cost.length ? `Pay ${formatRewardsText(cost)} → ${rwStr}` : rwStr;
    } else {
      label = o.label || o.id || "?";
    }
    if (o.available === false && o.unavailable_reason) label += ` (${o.unavailable_reason})`;
    return {label, value: o.id, disabled: o.available === false};
  });
  if (ctype === "influence_faction") return (choice.factions||[]).map(f=>({label:factionLabel(f),value:f}));
  if (ctype === "conditional") {
    const costs=formatRewardsText(choice.costs||[]), rewards=formatRewardsText(choice.rewards||[]);
    return [{label:`✓ Pay ${costs} → ${rewards}`,value:"accept"},{label:"✗ Skip",value:"decline"}];
  }
  if (ctype==="trash_card"||ctype==="discard_card"||ctype==="trash_to_acquire") {
    const items = (choice.available_cards||[]).map(item=>{const c=item.card||item;return{label:`${c.name} (${item.source||"hand"})`,value:c.id};});
    if (choice.can_skip) items.push({label: choice.skip_label||"Skip", value:"skip"});
    return items;
  }
  if (ctype==="accept_contract") {
    const items = (choice.available_contracts||[]).map(c=>({label:`${c.name} — ${contractCondition(c)}`,value:c.id}));
    if (choice.can_skip) items.push({label:"Skip (don't accept)",value:"skip"});
    return items;
  }
  if (ctype==="steal_intrigue"||ctype==="choose_opponent_discard") return (choice.valid_targets||[]).map(t=>({label:`${t.player_name} (${t.intrigue_count??t.hand_size})`,value:t.player_id}));
  if (ctype==="recall_agent") {
    const spaces=G.state?.board?.spaces||[];
    return (choice.placed_locations||[]).map(lid=>{const sp=spaces.find(s=>String(s.id)===String(lid));return{label:sp?.name||String(lid),value:String(lid)};});
  }
  if (ctype==="spy_post"||ctype==="play_spy") return (choice.available_posts||[]).map(p=>({label:p.post_name||p.post_id||p,value:p.post_id||p}));
  if (ctype==="play_spy_on_space") return (choice.eligible_spaces||[]).map(sp=>({label:sp.space_name||sp.space_id,value:sp.space_id}));
  if (ctype==="conditional_multi_choice") return (choice.options||[]).map(o=>({label:o.label||o.id,value:o.id}));
  if (ctype==="reveal_passive_choice") return (choice.options||[]).map(o=>({label:o.description||o.id,value:o.id}));
  if (ctype==="acquire_card") {
    const row=G.state?.board?.imperium_row||[];
    const target=choice.card;
    const cards=target?row.filter(c=>c.name===target):row;
    return cards.map(c=>({label:`${c.name} (${c.cost})`,value:c.id}));
  }
  return [{label:"OK",value:"ok"}];
}

function factionLabel(f) {
  return{fremen:"Fremen",bene_gesserit:"Bene Gesserit",spacing_guild:"Spacing Guild",emperor:"Emperor"}[f]||f;
}

// ─────────────── DISCARD MODAL ──────────────
function showDiscard(player, s) {
  const modal = document.getElementById("discard-modal");
  document.getElementById("discard-title").textContent = `${player.name}'s Discard (${player.discard_size})`;
  const cardsEl = document.getElementById("discard-cards");
  cardsEl.innerHTML = "";
  const cards = player.discard || [];
  if (cards.length) cards.forEach(c => cardsEl.appendChild(buildCard(c,"row-card",false,0)));
  else cardsEl.innerHTML = `<div style="color:var(--text-dim);padding:10px">Hidden for opponents</div>`;
  modal.classList.remove("hidden");
}
function closeDiscard() { document.getElementById("discard-modal").classList.add("hidden"); }

// ─────────────── CARD BUILDER ───────────────
function buildCard(card, extraClass, inAcquisition, persuasion) {
  const div = el("div",`card ${extraClass}`);
  const faction = card.factions?.[0] || "neutral";
  const affordable = !inAcquisition || card.cost <= persuasion;
  if (inAcquisition) {
    if (affordable) div.classList.add("affordable", "acquisition-card");
    else div.classList.add("unaffordable");
  }

  const hdr = el("div",`card-header ${faction}`);
  const nameEl = el("span","card-name"); nameEl.textContent = card.name;
  hdr.appendChild(nameEl);
  if (card.cost >= 0 && (card.cost > 0 || inAcquisition)) {
    const costEl = el("span","card-cost"+(card.cost===0?" free":"")); costEl.textContent = card.cost;
    hdr.appendChild(costEl);
  }
  div.appendChild(hdr);

  const body = el("div","card-body");

  // Faction badge(s) — show which faction(s) this card belongs to
  if (card.factions?.length) {
    const fRow = el("div","card-factions");
    card.factions.forEach(f => {
      const fn = normFaction(f);   // data uses both "Fremen" and "fremen"
      const tag = el("span",`card-faction-tag ${fn}`);
      const ico = FACTION_ICONS[fn] || "";
      const nm  = FACTION_SHORT[fn] || _prettyType(fn);
      tag.textContent = `${ico} ${nm}`.trim();
      fRow.appendChild(tag);
    });
    body.appendChild(fRow);
  }

  // Agent icons
  if (card.agent_icons?.length) {
    const iconRow = el("div","card-icons");
    card.agent_icons.forEach(ic => {
      const pip = el("span",`icon-pip ${ic}`);
      pip.textContent = agentIconLabel(ic);
      iconRow.appendChild(pip);
    });
    body.appendChild(iconRow);
  }

  function addEffects(effects, label) {
    if (!effects?.length) return;
    const lbl = el("div","card-section-label"); lbl.textContent = label; body.appendChild(lbl);
    const efDiv = el("div","card-effects");
    effects.forEach(e => {
      if (e && e.type === "choice") {
        // Expand each option as its own line with OR between
        (e.options || []).forEach((opt, idx) => {
          if (idx > 0) {
            const orLine = el("div","card-or-sep"); orLine.textContent = "── OR ──";
            efDiv.appendChild(orLine);
          }
          const line = el("div","effect-line");
          line.title = describeOptionText(opt);
          const bullet = el("span","ef-bullet"); bullet.textContent = "→";
          const text = el("span","ef-text");
          text.innerHTML = formatOptionRewardsHTML(opt);
          line.appendChild(bullet); line.appendChild(text);
          efDiv.appendChild(line);
        });
      } else {
        efDiv.appendChild(effectLine(e));
      }
    });
    body.appendChild(efDiv);
  }

  addEffects(card.agent_effects, "AGENT");
  addEffects(card.reveal_effects, "REVEAL");
  addEffects(card.on_acquire_effects, "ON BUY");

  div.appendChild(body);
  return div;
}

function buildIntrigueCard(card, currentPhase) {
  const div = el("div","card intrigue-card");

  // Header: name + phase tags
  const hdr = el("div","card-header intrigue-hdr");
  const nameEl = el("span","card-name"); nameEl.textContent = card.name;
  hdr.appendChild(nameEl);
  const phaseWrap = el("div","intrigue-phases");
  (card.phases||["Plot"]).forEach(p => {
    const tag = el("span","intrigue-phase-tag phase-" + String(p).toLowerCase());
    tag.textContent = String(p);
    phaseWrap.appendChild(tag);
  });
  hdr.appendChild(phaseWrap);
  div.appendChild(hdr);

  // Body: effects
  const body = el("div","card-body");
  const effects = card.effects || [];
  if (!effects.length) {
    const note = el("div","card-effects");
    note.style.cssText = "color:var(--text-dim);font-size:8px;font-style:italic";
    note.textContent = "No effects";
    body.appendChild(note);
  } else {
    const efDiv = el("div","card-effects");
    effects.forEach(e => efDiv.appendChild(intrigueEffectLine(e)));
    body.appendChild(efDiv);
  }
  div.appendChild(body);

  // Interactivity — Plot intrigues play during the agent turn, Combat
  // intrigues during the combat window.
  const phases = (card.phases||[]).map(p=>String(p).toLowerCase());
  const isPlot = phases.length === 0 || phases.includes("plot");
  const isCombat = phases.includes("combat");
  const playableNow = (currentPhase === "agent_turn" && isPlot)
                   || (currentPhase === "combat" && isCombat);
  if (playableNow) {
    div.classList.add("selectable");
    div.addEventListener("click", () => postAction({type:"play_intrigue",card_id:card.id}));
  } else {
    div.style.opacity = ".55";
  }
  return div;
}

function intrigueEffectLine(e) {
  // Intrigue effects have varied shapes; render a human-readable summary
  const line = el("div","effect-line");
  line.title = describeEffectText(e);   // hover for full plain-English text
  const bullet = el("span","ef-bullet"); bullet.textContent = "·";
  const text = el("span","ef-text");
  text.innerHTML = describeIntrigueEffect(e);
  line.appendChild(bullet);
  line.appendChild(text);
  return line;
}

function describeIntrigueEffect(e) {
  if (!e || typeof e !== "object") return String(e || "");
  const t = e.type || "";

  // Standard effects — delegate
  if (["resource","draw","influence","victory_point","trash","deploy_troops","combat_strength",
       "accept","council_seat","maker_hooks","recall_agent","spy","restrict","shield_wall"].includes(t)) {
    return describeEffectHTML(e);
  }

  // Choice: each option expanded with OR
  if (t === "choice") {
    const parts = (e.options||[]).map(o => {
      const cond = o.condition ? ` <em style="color:var(--text-dim)">(if ${o.condition.type})</em>` : "";
      return formatOptionRewardsHTML(o) + cond;
    });
    return parts.join(`<span style="color:var(--gold-dim);font-size:8px;margin:0 3px">OR</span>`);
  }

  // Action with cost → reward
  if (t === "action" || (e.cost && e.reward)) {
    const costHTML = (e.cost||[]).map(x => describeEffectHTML(x)).join("") || "";
    const rwHTML   = (e.reward||[]).map(x => describeEffectHTML(x)).join(" ") || "";
    return costHTML ? `<span class="ef-cost">${costHTML}&thinsp;→</span> ${rwHTML}` : rwHTML;
  }

  // Conditional reward
  if (t === "conditional_reward") {
    const cond = e.condition ? describeCheckShort(e.condition)
               : (e.check || []).map(describeCheckShort).join(" & ");
    const rwHTML = _rewardOf(e).map(describeEffectHTML).join(" ") || "";
    return `<span class="ef-if">if ${cond || "…"}:</span> ${rwHTML}`;
  }

  return describeEffectHTML(e) || t;
}

// ─────────────── EFFECT RENDERING ───────────
const FACTION_ICONS = {fremen:"🌵", bene_gesserit:"🔮", spacing_guild:"🚀", emperor:"👑"};

// Short readable names shown inline next to icons.
const RES_WORDS = {
  solari:"Solari", spice:"Spice", water:"Water", persuasion:"Persuasion",
  sword:"Sword", troop:"Troops", troops:"Troops", victory_point:"VP",
  agent:"Agent", worm:"Sandworm",
};
// Full names for plain-English tooltips.
const RES_NAMES = {
  solari:"Solari", spice:"Spice", water:"Water", persuasion:"Persuasion",
  sword:"combat strength (sword)", troop:"troop", troops:"troops",
  victory_point:"victory point", agent:"agent", worm:"sandworm",
};
const FACTION_NAMES = {
  fremen:"the Fremen", bene_gesserit:"the Bene Gesserit",
  spacing_guild:"the Spacing Guild", emperor:"the Emperor",
  any:"a faction of your choice", agent:"a faction where you have an agent",
};
// Plain-English phrasing for conditional `check` clauses.
const CHECK_NAMES = {
  spies_placed:"you have spies placed", cards_in_play:"the number of cards you have in play",
  contracts_completed:"contracts you have completed", units_in_conflict:"your units in the Conflict",
  faction_bond:"you have a matching faction card", fremen_bond:"you have a Fremen card",
  council_seat:"you hold the High Council seat", sent_an_agent_on:"you sent an agent to that space",
  maker_hook:"you have a Maker hook", discarded_faction_card:"you discarded a faction card",
  acquired_card:"you acquired a card this turn", influence:"your influence",
  recalled_spy:"you recalled a spy", alliance:"you hold an alliance",
  cards_in_deck:"cards in your deck", swordmaster:"you are a Swordmaster",
  spying:"you are spying", spies_on_board:"your spies on the board",
  buy_imperium:"you bought an Imperium Row card", deploy_units:"units you deploy",
  flip_conflict:"conflicts you have won", spice_must_flow_tokens:"your Spice Must Flow cards",
  recall:"agents you recall", gained_resource_this_turn:"resources you gained this turn",
};

function _plural(amt, word) { return amt === 1 ? word : word + "s"; }
function _cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
function _prettyType(t) { return _cap(String(t || "").replace(/_/g, " ")); }
function _fmtDeck(d) {
  if (Array.isArray(d)) return d.join("/");
  return {hand:"hand", played:"played cards", deck:"deck",
          discard:"discard pile", self:"this card", imperium:"Imperium Row"}[d] || d;
}
// cost/reward fields are sometimes a single object instead of a list.
function _asArr(v) { return Array.isArray(v) ? v : (v ? [v] : []); }
function _costOf(e)   { return _asArr(e.cost || e.costs); }
// Choice options store their payload under `reward`, `rewards`, or `effects`.
function _rewardOf(e) { return _asArr(e.reward || e.rewards || e.effects); }

// Short faction labels for compact inline condition text.
const FACTION_SHORT = {fremen:"Fremen", bene_gesserit:"Bene Gesserit",
  spacing_guild:"Guild", emperor:"Emperor"};
// Concise inline phrasing for conditional `check` clauses (shown on the card).
const CHECK_SHORT = {
  spies_placed:"spies placed", cards_in_play:"cards in play",
  contracts_completed:"contracts done", units_in_conflict:"units in Conflict",
  faction_bond:"faction card", fremen_bond:"Fremen card",
  council_seat:"Council seat", sent_an_agent_on:"agent sent there",
  maker_hook:"Maker hook", discarded_faction_card:"discarded faction card",
  acquired_card:"card acquired", influence:"influence",
  recalled_spy:"recalled spy", alliance:"alliance",
  cards_in_deck:"cards in deck", swordmaster:"Swordmaster",
  spying:"spying", spies_on_board:"spies on board",
  buy_imperium:"card bought", deploy_units:"units deployed",
  flip_conflict:"conflicts won", spice_must_flow_tokens:"Spice Must Flow cards",
  recall:"agents recalled", gained_resource_this_turn:"resource gained",
};

function _checkFaction(chk) {
  const f = chk.faction || (chk.type === "influence" ? chk.target : null);
  if (!f) return null;
  return String(f).toLowerCase();
}

function describeCheckText(chk) {
  if (!chk || typeof chk !== "object") return String(chk || "");
  let base = CHECK_NAMES[chk.type] || String(chk.type || "").replace(/_/g, " ");
  const fac = _checkFaction(chk);
  if (fac && FACTION_NAMES[fac]) {
    if (chk.type === "influence") base = `your influence with ${FACTION_NAMES[fac]}`;
    else if (chk.type === "discarded_faction_card") base = `you discarded a ${FACTION_SHORT[fac] || fac} card`;
  }
  return chk.amount != null ? `${base} ≥ ${chk.amount}` : base;
}

/** Concise inline condition label, e.g. "Bene Gesserit influence ≥2". */
function describeCheckShort(chk) {
  if (!chk || typeof chk !== "object") return String(chk || "");
  let base = CHECK_SHORT[chk.type] || String(chk.type || "").replace(/_/g, " ");
  const fac = _checkFaction(chk);
  if (fac && FACTION_SHORT[fac]) {
    if (chk.type === "influence") base = `${FACTION_SHORT[fac]} influence`;
    else if (chk.type === "discarded_faction_card") base = `discarded ${FACTION_SHORT[fac]} card`;
  }
  return chk.amount != null ? `${base} ≥${chk.amount}` : base;
}

function describeOptionText(o) {
  const cost = _costOf(o).map(x => describeEffectText(x, true)).filter(Boolean).join(", ");
  const rew  = _rewardOf(o).map(describeEffectText).filter(Boolean).join(", ");
  let s = cost ? `${cost} → ${rew}` : rew;
  if (o.condition && o.condition.type) s += ` (if ${describeCheckText(o.condition)})`;
  return s || o.id || "—";
}

/**
 * Full plain-English description of any effect. Used as hover tooltip.
 * `asCost` phrases resource/influence/VP as a payment (no "Gain" verb).
 */
function describeEffectText(e, asCost) {
  if (!e || typeof e !== "object") return String(e || "");
  if (e.description) return e.description;        // authoritative when present
  const t = e.type || "";
  const amt = e.amount != null ? e.amount : 1;
  const gain = asCost ? "" : "Gain ";        // cost clauses omit the verb
  const joinRew = arr => _asArr(arr).map(x => describeEffectText(x)).filter(Boolean).join(", ");

  switch (t) {
    case "resource": {
      const r = e.resource || "";
      if (r === "victory_point") return `${gain}${amt} ${_plural(amt,"victory point")}`;
      if (r === "troop" || r === "troops") return `${gain}${amt} ${_plural(amt,"troop")}`;
      return `${gain}${amt} ${RES_NAMES[r] || r}`;
    }
    case "draw":
      if (e.deck === "intrigue") return `Draw ${amt} Intrigue ${_plural(amt,"card")}`;
      if (e.deck === "imperium") return `Draw ${amt} ${_plural(amt,"card")} from the Imperium Row`;
      return `Draw ${amt} ${_plural(amt,"card")}`;
    case "influence":
      return `${gain}${amt} influence with ${FACTION_NAMES[e.target] || e.target || "a faction"}`;
    case "victory_point": return `${gain}${amt} ${_plural(amt,"victory point")}`;
    case "persuasion":    return `${gain}${amt} Persuasion`;
    case "combat_strength": return `Add ${amt} combat strength (sword)`;
    case "deploy_troops": return `Deploy ${amt} ${_plural(amt,"troop")} to the Conflict`;
    case "retreat":       return `Retreat ${amt} ${_plural(amt,"troop")} from the Conflict`;
    case "trash":
      if (e.deck === "self") return `Trash this card`;
      return `Trash ${amt} ${_plural(amt,"card")}${e.deck ? ` from your ${_fmtDeck(e.deck)}` : ""}`;
    case "trash_intrigue":return `Trash ${amt} Intrigue ${_plural(amt,"card")}`;
    case "discard":       return `Discard ${amt} ${_plural(amt,"card")}${e.deck ? ` from your ${_fmtDeck(e.deck)}` : ""}`;
    case "opponent_discard": return `Each opponent discards ${amt} ${_plural(amt,"card")}`;
    case "play":          return e.unit === "spy" ? `Place ${amt} ${_plural(amt,"spy")}` : `Play ${amt} ${e.unit || "unit"}`;
    case "spy":           return `Place ${amt} ${_plural(amt,"spy")}`;
    case "recall":        return `Recall ${amt} ${e.unit === "spy" ? _plural(amt,"spy") : _plural(amt, e.unit || "unit")}`;
    case "recall_agent":  return `Recall one of your agents`;
    case "council_seat":  return `Take the High Council seat`;
    case "signet":        return `Trigger your leader's Signet ability`;
    case "accept":        return `Sign a Contract`;
    case "control":       return `Take control of ${e.location === "current" ? "this location" : (e.location || "a location")}`;
    case "acquire_with_solari": return `You may acquire an Imperium Row card by paying Solari equal to its cost`;
    case "maker_hooks":   return `Gain a Maker hook`;
    case "steal":         return `Steal resources from an opponent`;
    case "return_to_hand":return `Return this card from play to your hand`;
    case "shield_wall":   return `Shield Wall effect`;
    case "restrict":      return `A restriction applies to this turn`;
    case "bypass_influence_requirment_rule": return `Ignore influence requirements when placing your agent this turn`;
    case "bypass_troops_deployment_rule":    return `You may deploy any troops you recruit this turn to the Conflict`;
    case "deck_manipulation": {
      const bits = [];
      if (e.look)    bits.push(`look at the top ${e.look} ${_plural(e.look,"card")} of your deck`);
      if (e.draw)    bits.push(`draw ${e.draw}`);
      if (e.trash)   bits.push(`trash ${e.trash}`);
      if (e.discard) bits.push(`discard ${e.discard}`);
      return bits.length ? _cap(bits.join(", ")) : "Manipulate your deck";
    }
    case "choice":
      return "Choose one — " + (e.options || []).map(describeOptionText).join("  OR  ");
    case "multiple":
      return `${joinRew(_rewardOf(e))} for each ${e.per || "unit"}`;
    case "action": case "exchange": case "trade": case "cost": {
      const cost = _costOf(e).map(x => describeEffectText(x, true)).filter(Boolean).join(", ");
      const rew  = _rewardOf(e).map(describeEffectText).filter(Boolean).join(", ");
      if (cost && rew) return `${cost} → ${rew}`;
      return rew || cost || _prettyType(t);
    }
    case "conditional": case "conditional_reward": {
      const checks = e.condition
        ? describeCheckText(e.condition)
        : (e.check || []).map(describeCheckText).join(" and ");
      const rew = joinRew(_rewardOf(e));
      return checks ? `If ${checks}: ${rew}` : rew;
    }
    default:
      return _prettyType(t);
  }
}

function effectLine(e) {
  const line = el("div","effect-line");
  line.title = describeEffectText(e);   // hover for full plain-English text
  const bullet = el("span","ef-bullet"); bullet.textContent = "·";
  const text = el("span","ef-text");
  text.innerHTML = describeEffectHTML(e);
  line.appendChild(bullet);
  line.appendChild(text);
  return line;
}

/** Compact inline rendering: icon + short word, so the card is self-explanatory. */
function describeEffectHTML(e) {
  if (!e || typeof e !== "object") return String(e || "");
  const t = e.type || "";
  const amt = e.amount != null ? e.amount : 1;
  const word = w => `<span class="ef-word">${w}</span>`;
  const qty  = `+${amt} `;

  if (t === "resource") {
    const r = e.resource || "";
    return `${qty}${resourceIconHTML(r)}${word(RES_WORDS[r] || r)}`;
  }
  if (t === "draw") {
    const icon = e.deck === "intrigue"
      ? `<i class="efx intrigue-draw"></i>` : `<i class="efx card-draw"></i>`;
    const lbl = e.deck === "intrigue" ? "Intrigue"
              : e.deck === "imperium" ? "from Row" : "Draw";
    return `${qty}${icon}${word(lbl)}`;
  }
  if (t === "influence") {
    const fIcon = FACTION_ICONS[e.target] || "★";
    return `${qty}${fIcon}${word("Influence")}`;
  }
  if (t === "victory_point") return `${qty}⭐${word("VP")}`;
  if (t === "persuasion")    return `${qty}<i class="efx persuasion"></i>${word("Persuasion")}`;
  if (t === "combat_strength") return `${qty}⚔${word("Sword")}`;
  if (t === "deploy_troops")  return `${qty}🗡${word("Deploy")}`;
  if (t === "retreat")        return `−${amt}🗡${word("Retreat")}`;
  if (t === "choice") {
    const parts = (e.options || []).map(o => formatOptionRewardsHTML(o));
    return parts.join(`<span class="ef-or">OR</span>`);
  }
  if (t === "action" || t === "exchange" || t === "trade" || t === "cost") {
    const costHTML = _costOf(e).map(describeEffectHTML).filter(Boolean).join(" ");
    const rwHTML   = _rewardOf(e).map(describeEffectHTML).filter(Boolean).join(" ");
    return costHTML ? `<span class="ef-cost">${costHTML}&thinsp;→</span> ${rwHTML}` : rwHTML;
  }
  if (t === "conditional") {
    const conds = (e.check || []).map(describeCheckShort).join(" & ");
    const rwHTML = _rewardOf(e).map(describeEffectHTML).filter(Boolean).join(" ");
    return `<span class="ef-if">if ${conds || "…"}:</span> ${rwHTML}`;
  }
  if (t === "multiple") {
    const rwHTML = _rewardOf(e).map(describeEffectHTML).filter(Boolean).join(" ");
    return `${rwHTML}${word("per " + (e.per || "unit"))}`;
  }
  if (t === "trash")          return `🗑${word(amt > 1 ? `Trash ×${amt}` : "Trash")}`;
  if (t === "trash_intrigue") return `🗑${word("Trash Intrigue")}`;
  if (t === "discard")        return `📤${word(amt > 1 ? `Discard ×${amt}` : "Discard")}`;
  if (t === "opponent_discard") return `📤${word("Opponents discard")}`;
  if (t === "accept")         return `📋${word("Sign Contract")}`;
  if (t === "council_seat")   return `🪑${word("Council seat")}`;
  if (t === "maker_hooks")    return `🪝${word("Maker hook")}`;
  if (t === "recall_agent")   return `↩${word("Recall agent")}`;
  if (t === "recall")         return `↩${word("Recall " + (e.unit || "spy"))}`;
  if (t === "play" || t === "spy") return `🕵${word(e.unit === "spy" || t === "spy" ? "Place spy" : "Play")}`;
  if (t === "signet")         return `💍${word("Signet")}`;
  if (t === "control")        return `🚩${word("Control space")}`;
  if (t === "acquire_with_solari") return `🛒${word("Buy w/ Solari")}`;
  if (t === "deck_manipulation") return `🃏${word("Sift deck")}`;
  if (t === "return_to_hand") return `↩${word("Return to hand")}`;
  if (t === "restrict")       return `⚠${word("Restriction")}`;
  if (t === "steal")          return `⚡${word("Steal")}`;
  if (t === "shield_wall")    return `🛡${word("Shield Wall")}`;
  if (t === "bypass_influence_requirment_rule") return `⚙${word("Ignore influence req.")}`;
  if (t === "bypass_troops_deployment_rule")    return `⚙${word("Free deploy")}`;
  return word(_prettyType(t));
}

function resourceIconHTML(res) {
  const map = {
    solari:        `<i class="efx solari"></i>`,
    spice:         `<i class="efx spice"></i>`,
    water:         `💧`,
    troop:         `🗡`,
    persuasion:    `<i class="efx persuasion"></i>`,
    sword:         `⚔`,
    worm:          `🪱`,
    agent:         `📍`,
    victory_point: `⭐`,
  };
  return map[res] || res;
}

/** Render one choice option (reward ± cost) as HTML icons. */
function formatOptionRewardsHTML(opt) {
  const rewardArr = _rewardOf(opt);
  const costArr   = _costOf(opt);
  const rewHTML = rewardArr.map(e => describeEffectHTML(e)).filter(Boolean).join(" ");
  if (costArr.length) {
    const costHTML = costArr.map(e => describeEffectHTML(e)).filter(Boolean).join("");
    return `<span class="ef-cost">${costHTML}&thinsp;→</span> ${rewHTML}`;
  }
  return rewHTML || (opt.id ? `<em style="color:var(--text-dim)">${opt.id}</em>` : "—");
}

function formatRewardsText(effects) {
  if (!Array.isArray(effects)) return String(effects || "");
  return effects.map(e => {
    if (!e || typeof e !== "object") return String(e);
    const t = e.type || "", amt = e.amount ?? 1, res = e.resource || "";
    if (t === "resource") {
      const sym = {solari:"●",spice:"◆",water:"💧",troop:"🗡",persuasion:"◇",sword:"⚔",worm:"🪱",agent:"📍"}[res] || res[0] || "";
      return `+${amt}${sym}`;
    }
    if (t === "victory_point") return `+${amt}⭐`;
    if (t === "influence") return `↑${FACTION_ICONS[e.target]||"★"}`;
    if (t === "draw") return e.deck==="intrigue" ? `+${amt}🃏` : `+${amt}🂠`;
    if (t === "accept") return `📋`;
    if (t === "victory_point") return `+${amt}⭐`;
    return t;
  }).filter(Boolean).join(" ") || "—";
}

// ─────────────── EVENT LOG ──────────────────
function appendEvents(events) {
  const logEl = document.getElementById("event-log");
  events.forEach(ev => {
    const div = el("div",`ev ev-${evClass(ev.type)}`);
    div.textContent = describeEvent(ev);
    logEl.appendChild(div);
    while (logEl.children.length > 80) logEl.removeChild(logEl.firstChild);
  });
  logEl.scrollTop = logEl.scrollHeight;
}

function evClass(t) {
  if (["combat_resolved"].includes(t)) return "combat";
  if (["acquire_card","acquire_contract"].includes(t)) return "acquire";
  if (["reveal","auto_reveal"].includes(t)) return "reveal";
  if (["contract_completed"].includes(t)) return "contract";
  if (["new_round"].includes(t)) return "round";
  if (["bot_action","reveal"].includes(t)) return "bot";
  return "";
}

function describeEvent(ev) {
  const t = ev.type;
  if (t === "place_agent")  return `${ev.player} → ${ev.location} [${ev.card}]`;
  if (t === "bot_action") {
    let msg = `🤖 ${ev.player}: ${ev.card} → ${ev.location}`;
    if (ev.troops > 0) msg += ` (${ev.troops}🗡)`;
    if (ev.effects) msg += ` | ${ev.effects}`;
    return msg;
  }
  if (t === "reveal")         return `${ev.player} reveals (${ev.persuasion} persuasion)`;
  if (t === "auto_reveal")    return `${ev.player} auto-reveals`;
  if (t === "acquire_card")   return `${ev.player} buys ${ev.card} [${ev.cost}]`;
  if (t === "acquire_contract") return `${ev.player} takes contract`;
  if (t === "play_intrigue")  return `${ev.player} plays ${ev.card}`;
  if (t === "combat_resolved") {
    const tied = ev.tied || ev.winner === "(tied)";
    return tied ? `⚔ ${ev.conflict}: Tie!` : `⚔ ${ev.conflict}: ${ev.winner} wins!`;
  }
  if (t === "contract_completed") return `🎉 ${ev.player}: ${ev.contract}!`;
  if (t === "recall")         return `${ev.player} recalls`;
  if (t === "new_round")      return `═══ Round ${ev.round} ═══`;
  if (t === "new_conflict")   return `Conflict: ${ev.conflict}`;
  return `${t}`;
}

// ─────────────── COMBAT TOAST ────────────────
function showCombatToast(ev) {
  const toast = document.getElementById("combat-toast");
  if (!toast) return;
  const winner = ev.winner || "(tied)";
  const lines = [`⚔ ${ev.conflict || "Conflict"} resolved`];
  if (ev.strength_summary) {
    ev.strength_summary.forEach(p => {
      const you = p.is_human ? " (YOU)" : "";
      lines.push(`  ${p.name}${you}: ${p.strength}`);
    });
  }
  const isTied = ev.tied || winner === "(tied)";
  lines.push(isTied ? "🤝 Tied — no winner" : `🏆 Winner: ${winner}`);
  // Show worm doubling note
  const wormPlayers = (G.conflictHistory[G.conflictHistory.length - 1] || {}).worm_players || [];
  if (wormPlayers.length) {
    lines.push(`🪱 ${wormPlayers.join(", ")}: rewards ×2!`);
  }
  toast.innerHTML = lines.join("<br>");
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 6000);
}

// ─────────────── GAME OVER ────────────────
function showGameOver(data) {
  if (!data) return;
  const overlay = document.getElementById("gameover-overlay");
  if (!overlay) return;
  const titleEl = document.getElementById("gameover-title");
  const subtitleEl = document.getElementById("gameover-subtitle");
  const scoresEl = document.getElementById("gameover-scores");

  if (data.is_human_winner) {
    titleEl.textContent = "🏆 VICTORY!";
    titleEl.style.color = "var(--gold)";
  } else {
    titleEl.textContent = "⚔ GAME OVER";
    titleEl.style.color = "var(--text-dim)";
  }

  const winners = data.winner_names || [];
  subtitleEl.textContent = winners.length > 0
    ? `Winner${winners.length > 1 ? "s" : ""}: ${winners.join(" & ")} • After ${data.total_rounds} rounds`
    : `${data.total_rounds} rounds complete`;

  scoresEl.innerHTML = "";
  (data.ranked_players || []).forEach((p, i) => {
    const row = el("div", "go-score-row" + (p.is_human ? " go-human" : ""));
    const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i+1}.`;
    row.innerHTML = `
      <span class="go-rank">${medal}</span>
      <span class="go-name">${p.name}${p.is_human ? " (You)" : ""}</span>
      <span class="go-vp">⭐ ${p.vp} VP</span>
      <span class="go-res">${p.solari}● ${p.spice}◆</span>
    `;
    scoresEl.appendChild(row);
  });

  overlay.classList.remove("hidden");
}

// ─────────────── UTILITIES ──────────────────
function el(tag, className) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  return e;
}
function shortName(name) { return name?.length > 9 ? name.slice(0,8)+"…" : (name||"?"); }
function showError(msg) {
  const toast = el("div","");
  toast.style.cssText = "position:fixed;top:10px;right:10px;z-index:9999;max-width:280px;background:#2a0a0a;border:1px solid #c04040;color:#f08080;padding:9px 12px;border-radius:5px;font-size:11px;";
  toast.textContent = "⚠ " + msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// Build a plain-text VP breakdown by source for tooltips / stats.
function vpBreakdownText(p) {
  const src = p.vp_sources || {};
  const lines = Object.entries(src).filter(([,v]) => v).map(([k,v]) => `  ${k}: ${v}`);
  if (!lines.length) return `Victory Points: ${p.victory_points} (no sources yet)`;
  return `Victory Points: ${p.victory_points}\n` + lines.join("\n");
}

function showFullState() {
  if (!G.state) return;
  const h = G.state.players.find(p => p.player_id === G.state.viewer_player_id);
  if (!h) return;
  alert(
    `${vpBreakdownText(h)}\n\n` +
    `Sol:${h.solari} Spi:${h.spice} Wat:${h.water}\n` +
    `Troops: ${h.troops_in_garrison} garrison / ${h.troops_in_conflict} conflict\n` +
    `Agents: ${h.agents_available}/${h.total_available_agents}\n` +
    `Influence: Fr${h.influence?.fremen} BG${h.influence?.bene_gesserit} GU${h.influence?.spacing_guild} EM${h.influence?.emperor}`
  );
}
