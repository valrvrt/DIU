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
  const evts = snap.events || [];
  appendEvents(evts);
  render();
  if (G.pendingChoice) showChoiceModal(G.pendingChoice);
  // Check for combat events to show toast
  const combatEv = evts.find(e => e.type === "combat_resolved");
  if (combatEv) showCombatToast(combatEv);
  // Show game-over overlay
  if (G.state?.game_over) showGameOver(G.state.game_over_data);
}

function render() {
  const s = G.state;
  if (!s) return;
  renderTopBar(s);
  renderContractDisplay(s);
  renderFactionSpaces(s);
  renderNeutralSpaces(s);
  renderCombatZone(s);
  renderImperiumRow(s);
  renderPlayerArea(s);
  updateActionButtons(s);
}

// ─────────────── TOP BAR ────────────────────
function renderTopBar(s) {
  document.getElementById("round-label").textContent = `Round ${s.round}`;
  document.getElementById("phase-badge").textContent = phaseLabel(s.available_actions?.phase || s.phase);

  const bar = document.getElementById("opponents-bar");
  bar.innerHTML = "";
  s.players.forEach((p, i) => {
    if (p.player_id === s.viewer_player_id) return;
    const chip = el("div","opponent-chip");
    const leaderName = p.leader?.name ? ` (${p.leader.name})` : "";
    chip.innerHTML = `
      <span class="chip-color" style="background:var(--${G.playerColors[i]})"></span>
      <span>${shortName(p.name)}${leaderName}</span>
      <span class="chip-vp">⭐${p.victory_points}</span>
      <span class="chip-sol" style="color:var(--solari)">●${p.solari}</span>
      <span class="chip-spi" style="color:var(--spice)">◆${p.spice}</span>
      <span style="color:var(--text-dim)">🃏${p.hand_size}</span>
    `;
    bar.appendChild(chip);
  });
}

function phaseLabel(phase) {
  const map = {
    agent_turn:"Agent Phase", acquisition:"Acquisition", player_turns:"Playing",
    combat:"Combat", recall:"Recall", game_over:"GAME OVER", choice:"Choose…",
  };
  return map[phase] || phase || "—";
}

// ─────────────── CONTRACT DISPLAY (board Trade panel) ────────────
function renderContractDisplay(s) {
  const panel = document.getElementById("contract-display");
  if (!panel) return;
  panel.innerHTML = "";
  const aa = s.available_actions || {};
  const inAcq = aa.phase === "acquisition";
  const contracts = s.board?.contract_row || [];

  if (!contracts.length) {
    const empty = el("div",""); empty.style.cssText = "font-size:8px;color:var(--text-dim)";
    empty.textContent = "None available";
    panel.appendChild(empty);
    return;
  }

  contracts.forEach(c => {
    const item = el("div", "contract-item" + (inAcq ? " contract-takeable" : ""));
    item.innerHTML = `
      <div class="ci-name">${c.name}${inAcq ? ' <span class="ci-take-hint">click to take</span>' : ""}</div>
      <div class="ci-cond">${contractCondition(c)}</div>
      <div class="ci-reward">→ ${formatRewardsText(c.rewards || [])}</div>
    `;
    if (inAcq) item.addEventListener("click", () => promptAcceptContract(c));
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
    spaces.forEach(sp => cont.appendChild(renderBoardSpace(sp, s)));
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
    const node = renderBoardSpace(sp, s);

    if (icon === "green") {
      landsraadEl.appendChild(node);
    } else if (name.includes("shipping") || name.includes("accept")) {
      shippingEl.appendChild(node);
    } else if (icon === "yellow") {
      desertEl.appendChild(node);
    } else {
      cityEl.appendChild(node);
    }
  });
}

// ─────────────── BOARD SPACE ────────────────
function renderBoardSpace(sp, s) {
  const div = el("div","board-space");
  const aa = s.available_actions || {};

  const isValid = G.selectedCard && G.selectedCard.validLocations.includes(String(sp.id));
  if (isValid) div.classList.add("valid-target");
  if (sp.occupied_by) div.classList.add("occupied");

  // Header
  const hdr = el("div","sp-header");
  const nameEl = el("span","sp-name"); nameEl.textContent = sp.name;
  hdr.appendChild(nameEl);
  div.appendChild(hdr);

  // Rewards (compact icon row)
  const rwArr = sp.reward || [];
  if (rwArr.length) {
    const rw = el("div","sp-rewards");
    rwArr.forEach(e => {
      const ico = el("span",""); ico.innerHTML = describeEffectHTML(e);
      rw.appendChild(ico);
    });
    div.appendChild(rw);
  }

  // Influence/alliance requirements (e.g., 2+ Fremen for Sietch Tabr)
  const checks = sp.check || [];
  if (checks.length) {
    const req = el("div","sp-checks");
    checks.forEach(c => {
      const t = c.type || "";
      if (t === "influence") {
        const ico = el("span","sp-check-inf");
        ico.innerHTML = `<i class="efx influence"></i>${c.amount||1}+ ${factionLabel(c.target||"")}`;
        req.appendChild(ico);
      } else if (t === "council_seat") {
        const ico = el("span","sp-check-inf"); ico.textContent = "🪑 Council seat";
        req.appendChild(ico);
      } else if (t === "alliance") {
        const ico = el("span","sp-check-inf"); ico.textContent = `★ ${factionLabel(c.target||"")} alliance`;
        req.appendChild(ico);
      }
    });
    if (req.children.length) div.appendChild(req);
  }

  // Combat marker
  if (sp.is_combat_space) {
    const marker = el("span","");
    marker.innerHTML = "⚔ ";
    marker.style.cssText = "font-size:8px;color:#e05050;";
    div.insertBefore(marker, div.firstChild);
  }

  // Spice bonus (accumulated on maker spaces)
  if (sp.spice_bonus > 0) {
    const bonus = el("div","sp-spice-bonus");
    bonus.innerHTML = `<i class="efx spice"></i> +${sp.spice_bonus}`;
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
      <div class="cf-lvl">Level ${conflict.level}</div>
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
  document.getElementById("your-name-label").textContent = (human.name || "").toUpperCase() + leaderStr;

  // Resources bar
  const resBar = document.getElementById("player-resources");
  if (resBar) {
    const aa2 = s.available_actions || {};
    const agentsStr = `${human.agents_available}/${human.total_available_agents}`;
    resBar.innerHTML = `
      <span class="res-chip"><i class="efx vp">⭐</i><span class="rc-val">${human.victory_points}</span></span>
      <span class="res-chip"><i class="efx solari"></i><span class="rc-val">${human.solari}</span></span>
      <span class="res-chip"><i class="efx spice"></i><span class="rc-val">${human.spice}</span></span>
      <span class="res-chip">💧<span class="rc-val">${human.water}</span></span>
      <span class="res-chip">🏰<span class="rc-val">${human.troops_in_garrison}</span>garrison</span>
      <span class="res-chip">📍<span class="rc-val">${agentsStr}</span>agents</span>
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
    const div = buildIntrigueCard(c, aa.phase === "agent_turn");
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
  document.getElementById("reveal-btn").classList.toggle("hidden", aa.phase !== "agent_turn");
  document.getElementById("end-acq-btn").classList.toggle("hidden", aa.phase !== "acquisition");
}

function doReveal() { postAction({ type: "reveal" }); clearSelectedCard(); }
function endAcquisition() { postAction({ type: "end_acquisition" }); }

// ─────────────── CARD SELECTION / PLACEMENT ─────────────
function selectCard(card, validLocations) {
  if (G.selectedCard?.id === card.id) { clearSelectedCard(); return; }
  G.selectedCard = { id: card.id, validLocations };
  render();
}
function clearSelectedCard() { G.selectedCard = null; render(); }

function placeAgent(cardId, locationId, isCombatSpace) {
  if (isCombatSpace) {
    const maxTroops = G.state?.available_actions?.max_troops || 0;
    if (maxTroops > 0) {
      showTroopPicker(cardId, locationId, maxTroops);
      return;
    }
  }
  postAction({ type: "place_agent", card_id: cardId, location_id: String(locationId), troops: 0 });
  clearSelectedCard();
}

function showTroopPicker(cardId, locationId, maxTroops) {
  const modal = document.getElementById("choice-modal");
  document.getElementById("choice-title").textContent = "Deploy Troops to Conflict?";
  document.getElementById("choice-desc").textContent = `You may send up to ${maxTroops} troops from garrison to the conflict.`;
  const optEl = document.getElementById("choice-options");
  optEl.innerHTML = "";
  for (let t = 0; t <= maxTroops; t++) {
    const btn = el("button","choice-btn");
    btn.textContent = t === 0 ? "No troops" : `${t} troop${t > 1 ? "s" : ""}`;
    btn.addEventListener("click", () => {
      modal.classList.add("hidden");
      postAction({ type: "place_agent", card_id: cardId, location_id: String(locationId), troops: t });
      clearSelectedCard();
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
    const rw = o.rewards || o.reward || [];
    const cost = o.costs || o.cost || [];
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
    return (choice.available_cards||[]).map(item=>{const c=item.card||item;return{label:`${c.name} (${item.source||"hand"})`,value:c.id};});
  }
  if (ctype==="accept_contract") return (choice.available_contracts||[]).map(c=>({label:`${c.name} — ${contractCondition(c)}`,value:c.id}));
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
  if (inAcquisition) div.classList.add(affordable ? "affordable acquisition-card" : "unaffordable");

  const hdr = el("div",`card-header ${faction}`);
  const nameEl = el("span","card-name"); nameEl.textContent = card.name;
  hdr.appendChild(nameEl);
  if (card.cost >= 0 && (card.cost > 0 || inAcquisition)) {
    const costEl = el("span","card-cost"+(card.cost===0?" free":"")); costEl.textContent = card.cost;
    hdr.appendChild(costEl);
  }
  div.appendChild(hdr);

  const body = el("div","card-body");

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
    effects.forEach(e => efDiv.appendChild(effectLine(e)));
    body.appendChild(efDiv);
  }

  addEffects(card.agent_effects, "AGENT");
  addEffects(card.reveal_effects, "REVEAL");
  addEffects(card.on_acquire_effects, "ON BUY");

  div.appendChild(body);
  return div;
}

function buildIntrigueCard(card, isAgentPhase) {
  const div = el("div","card intrigue-card");
  const hdr = el("div","card-header");
  const nameEl = el("span","card-name"); nameEl.textContent = card.name;
  hdr.appendChild(nameEl);
  const phaseTag = el("span","intrigue-phase");
  phaseTag.textContent = (card.phases||[]).join("/") || "Plot";
  hdr.appendChild(phaseTag);
  div.appendChild(hdr);

  const body = el("div","card-body");
  const efDiv = el("div","card-effects");
  (card.effects||[]).slice(0,3).forEach(e => efDiv.appendChild(effectLine(e)));
  body.appendChild(efDiv);
  div.appendChild(body);

  const phases = (card.phases||[]).map(p=>String(p).toLowerCase());
  const isPlot = phases.length === 0 || phases.includes("plot");
  if (isAgentPhase && isPlot) {
    div.classList.add("selectable");
    div.addEventListener("click", () => postAction({type:"play_intrigue",card_id:card.id}));
  } else if (!isPlot) {
    div.style.opacity = ".55";
  }
  return div;
}

// ─────────────── EFFECT RENDERING ───────────
function effectLine(e) {
  const line = el("div","effect-line");
  const bullet = el("span","ef-bullet"); bullet.textContent = "·";
  const text = el("span","ef-text");
  text.innerHTML = describeEffectHTML(e);
  line.appendChild(bullet);
  line.appendChild(text);
  return line;
}

function describeEffectHTML(e) {
  if (!e || typeof e !== "object") return String(e || "");
  const t = e.type || "";
  const amt = e.amount != null ? e.amount : 1;

  if (t === "resource") {
    const res = e.resource || "";
    const iconH = resourceIconHTML(res);
    return `${iconH}${amt > 1 ? ` ×${amt}` : ""}`;
  }
  if (t === "draw") {
    if (e.deck === "intrigue") return `<i class="efx intrigue-draw"></i>${amt > 1 ? ` ×${amt}` : ""}`;
    return `<i class="efx card-draw"></i>${amt > 1 ? ` ×${amt}` : ""}`;
  }
  if (t === "influence") return `<i class="efx influence"></i> ${factionLabel(e.target||"")}`;
  if (t === "victory_point") return `⭐×${amt}`;
  if (t === "choice") {
    const parts = (e.options||[]).slice(0,3).map(o => {
      const rw = o.reward || [];
      const cost = o.cost || [];
      const rwStr = formatRewardsText(rw);
      if (cost.length) return `(${formatRewardsText(cost)}→${rwStr})`;
      return rwStr || o.id || "?";
    });
    return `Choose: ${parts.join(" / ")}`;
  }
  if (t === "conditional") return `Optional bonus`;
  if (t === "trash") return `🗑 ×${amt}`;
  if (t === "accept") return `📋 take contract`;
  if (t === "council_seat") return `🪑 Council`;
  if (t === "maker_hooks") return `🪝 Maker hooks`;
  if (t === "recall_agent") return `↩ recall agent`;
  if (t === "restrict") return `⚠ restrict`;
  if (t === "deploy_troops") return `🗡 +${amt} to battle`;
  if (t === "combat_strength") return `⚔ +${amt} strength`;
  if (t === "spy") return `🕵 spy post`;
  if (t === "steal") return `steal`;
  if (t === "shield_wall") return `🛡 shield`;
  return t;
}

function resourceIconHTML(res) {
  const map = {
    solari:   `<i class="efx solari"></i>`,
    spice:    `<i class="efx spice"></i>`,
    water:    `💧`,
    troop:    `🗡`,
    persuasion: `<i class="efx persuasion"></i>`,
    sword:    `⚔`,
    worm:     `🪱`,
    agent:    `📍`,
    victory_point: `⭐`,
  };
  return map[res] || res;
}

function formatRewardsText(effects) {
  if (!Array.isArray(effects)) return String(effects || "");
  return effects.map(e => {
    if (!e || typeof e !== "object") return String(e);
    const t = e.type || "", amt = e.amount ?? 1, res = e.resource || "";
    if (t === "resource") return `+${amt}${res[0]||""}`;
    if (t === "victory_point") return `${amt}VP`;
    if (t === "influence") return `+inf`;
    if (t === "draw") return `+${amt}card`;
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
  toast.innerHTML = lines.join("<br>");
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 5000);
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

function showFullState() {
  if (!G.state) return;
  const h = G.state.players.find(p => p.player_id === G.state.viewer_player_id);
  if (!h) return;
  alert(`VP:${h.victory_points} Sol:${h.solari} Spi:${h.spice} Wat:${h.water}\nTroops: ${h.troops_in_garrison} garrison / ${h.troops_in_conflict} conflict\nAgents: ${h.agents_available}/${h.total_available_agents}\nInfluence: Fr${h.influence?.fremen} BG${h.influence?.bene_gesserit} GU${h.influence?.spacing_guild} EM${h.influence?.emperor}`);
}
