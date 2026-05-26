/* ══════════════════════════════════════════════════════════
   DUNE: Imperium Uprising — frontend app
   ══════════════════════════════════════════════════════════ */

// ─────────────── global state ───────────────
let G = {
  state: null,          // full game state from server
  selectedCard: null,   // {id, validLocations: [str]} card selected in hand
  pendingChoice: null,  // choice waiting for resolution
  playerColors: ["p0","p1","p2","p3"],
  playerCount: 3,
  humanId: null,
};

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
  const snap = await api("POST", "/api/new-game", { player_count: G.playerCount, human_name: name });
  if (snap) {
    G.humanId = snap.state.viewer_player_id;
    document.getElementById("setup-overlay").classList.add("hidden");
    document.getElementById("game").classList.remove("hidden");
    applySnapshot(snap);
  }
});

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
  appendEvents(snap.events || []);
  render();
  if (G.pendingChoice) showChoiceModal(G.pendingChoice);
}

function render() {
  const s = G.state;
  if (!s) return;

  renderTopBar(s);
  renderContractsStrip(s);
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
    const chip = el("div", "opponent-chip");
    chip.innerHTML = `
      <span class="chip-color" style="background:var(--${G.playerColors[i]})"></span>
      <span title="${p.name}">${shortName(p.name)}</span>
      <span class="chip-vp">⭐${p.victory_points}</span>
      <span class="chip-sol">🪙${p.solari}</span>
      <span class="chip-spi">🌶${p.spice}</span>
      <span class="chip-wat">💧${p.water}</span>
      <span class="chip-sol" style="color:var(--text-dim)">🃏${p.hand_size}</span>
    `;
    bar.appendChild(chip);
  });
}

function phaseLabel(phase) {
  const map = {
    agent_turn: "Agent Phase",
    acquisition: "Acquisition Phase",
    player_turns: "Player Turns",
    combat: "Combat",
    recall: "Recall",
    game_over: "GAME OVER",
    choice: "Waiting for Choice…",
  };
  return map[phase] || phase || "—";
}

// ─────────────── CONTRACTS STRIP ────────────
function renderContractsStrip(s) {
  const row = document.getElementById("contract-row");
  row.innerHTML = "";
  const contracts = s.board?.contract_row || [];
  contracts.forEach(c => {
    const chip = el("div", "contract-chip");
    chip.innerHTML = `
      <span>📋 ${c.name}</span>
      <span class="cond">${contractCondition(c)}</span>
      <span class="reward">→ ${formatRewards(c.rewards || [])}</span>
    `;
    chip.addEventListener("click", () => promptAcceptContract(c));
    row.appendChild(chip);
  });
}

function contractCondition(c) {
  if (c.completion_type === "immediate") return "immediate";
  if (c.completion_type === "location")  return `visit ${c.completion_target}`;
  if (c.completion_type === "harvest")   return `harvest ${c.required_spice} spice`;
  if (c.completion_type === "acquire_card") return `buy "${c.completion_target}"`;
  return c.completion_type || "—";
}

// ─────────────── FACTION SPACES ─────────────
function renderFactionSpaces(s) {
  const factions = ["fremen","bene_gesserit","spacing_guild","emperor"];
  factions.forEach(f => {
    // Influence track
    const trackEl = document.getElementById(`inf-${f}`);
    if (trackEl) renderInfluenceTrack(trackEl, f, s);

    // Spaces
    const container = document.getElementById(`spaces-${f}`);
    if (!container) return;
    container.innerHTML = "";
    const spaces = (s.board?.spaces || []).filter(sp => normalFaction(sp.faction) === f);
    spaces.forEach(sp => container.appendChild(renderBoardSpace(sp, s)));
  });
}

function normalFaction(f) {
  if (!f) return null;
  return f.toLowerCase().replace(/ /g,"_").replace("benegesserit","bene_gesserit")
          .replace("spacingguild","spacing_guild");
}

function renderInfluenceTrack(trackEl, faction, s) {
  trackEl.innerHTML = "";
  s.players.forEach((p, idx) => {
    const factionKey = {
      fremen: "fremen", bene_gesserit: "bene_gesserit",
      spacing_guild: "spacing_guild", emperor: "emperor"
    }[faction];
    const level = p.influence?.[factionKey] ?? 0;
    const alliance = p.alliances?.[factionKey] ?? false;
    const row = el("div", "inf-row");
    const nameSpan = el("span", "inf-player-label");
    nameSpan.textContent = p.name[0];
    nameSpan.style.color = `var(--${G.playerColors[idx]})`;
    row.appendChild(nameSpan);
    for (let i = 0; i < 4; i++) {
      const pip = el("span", "inf-pip" + (i < level ? " filled" : ""));
      if (i < level) pip.style.background = `var(--${G.playerColors[idx]})`;
      row.appendChild(pip);
    }
    if (alliance) {
      const star = el("span", "alliance-star");
      star.textContent = "★";
      row.appendChild(star);
    }
    trackEl.appendChild(row);
  });
}

// ─────────────── NEUTRAL SPACES ─────────────
function renderNeutralSpaces(s) {
  const cityIds   = [22, 14, 13, 12, "22","14","13","12"];  // Arrakeen, Spice Refinery, Research Stn, Sietch Tabr
  const desertIds = [9, 10, 11, 20, 21, "9","10","11","20","21"]; // Deep Desert, Haga, Imperial Basin, Shipping, Accept
  const councilIds= [15, 16, 17, 18, 19, "15","16","17","18","19"]; // High Council, etc.

  const cityEl    = document.getElementById("spaces-city");
  const councilEl = document.getElementById("spaces-council");
  cityEl.innerHTML = "";
  councilEl.innerHTML = "";

  const neutral = (s.board?.spaces || []).filter(sp => !normalFaction(sp.faction));
  neutral.forEach(sp => {
    const sid = parseInt(sp.id) || sp.id;
    const node = renderBoardSpace(sp, s);
    if (councilIds.includes(sid) || councilIds.includes(sp.id)) {
      councilEl.appendChild(node);
    } else {
      cityEl.appendChild(node);
    }
  });
}

// ─────────────── BOARD SPACE ────────────────
function renderBoardSpace(sp, s) {
  const div = el("div", "board-space");
  const aa = s.available_actions || {};

  // Check if this is a valid target for the selected card
  const isValid = G.selectedCard &&
    G.selectedCard.validLocations.includes(String(sp.id));
  if (isValid) div.classList.add("valid-target");
  if (sp.occupied_by) div.classList.add("occupied");

  // Header
  const hdr = el("div","sp-header");
  const nameEl = el("span","sp-name"); nameEl.textContent = sp.name;
  const iconEl = el("span","sp-icon"); iconEl.textContent = agentIconLabel(sp.agent_icon);
  hdr.appendChild(nameEl); hdr.appendChild(iconEl);
  div.appendChild(hdr);

  // Badges
  const badges = el("div","sp-badges");
  if (sp.is_combat_space) { const b = el("span","badge-small badge-combat"); b.textContent="⚔ Combat"; badges.appendChild(b); }
  if (sp.is_maker_space)  { const b = el("span","badge-small badge-maker");  b.textContent="☆ Maker";  badges.appendChild(b); }
  if (sp.is_critical_location) { const b = el("span","badge-small badge-critical"); b.textContent="⬟ Critical"; badges.appendChild(b); }
  if (badges.children.length) div.appendChild(badges);

  // Spice bonus on maker
  if (sp.is_maker_space && sp.spice_bonus > 0) {
    const sb = el("div","sp-spice-bonus"); sb.textContent = `🌶 +${sp.spice_bonus} bonus`;
    div.appendChild(sb);
  }

  // Cost (if any)
  if (sp.cost && sp.cost.length) {
    const costBadge = el("span","badge-small badge-cost");
    costBadge.textContent = "Cost: " + formatRewards(sp.cost);
    div.appendChild(costBadge);
  }

  // Rewards
  if (sp.reward && sp.reward.length) {
    const rw = el("div","sp-rewards"); rw.textContent = formatRewards(sp.reward);
    div.appendChild(rw);
  }

  // Occupant
  if (sp.occupied_by) {
    const pidx = s.players.findIndex(p => p.player_id === sp.occupied_by);
    const name = s.players[pidx]?.name || sp.occupied_by;
    const occ = el("span", `sp-occupant occ-${Math.max(pidx,0)}`);
    occ.textContent = "🧍" + shortName(name);
    div.appendChild(occ);
  }
  // Infiltrated by spy
  if (sp.infiltrated_by) {
    const pidx = s.players.findIndex(p => p.player_id === sp.infiltrated_by);
    const name = s.players[pidx]?.name || sp.infiltrated_by;
    const inf = el("span","sp-occupant"); inf.textContent = "🕵" + shortName(name);
    inf.style.top = sp.occupied_by ? "14px" : "3px";
    div.appendChild(inf);
  }

  // Click: place agent here
  div.addEventListener("click", () => {
    if (G.selectedCard && isValid) {
      placeAgent(G.selectedCard.id, sp.id);
    }
  });

  return div;
}

function agentIconLabel(icon) {
  const map = {
    fremen: "🌵", bene_gesserit: "🔮", spacing_guild: "🚀", emperor: "👑",
    yellow: "🌶", blue: "🏙", green: "🏛", spy: "🕵", city: "🏙",
  };
  return map[icon?.toLowerCase()] || icon || "◦";
}

// ─────────────── COMBAT ZONE ────────────────
function renderCombatZone(s) {
  const conflict = s.board?.current_conflict;
  const cfEl = document.getElementById("current-conflict");
  if (conflict) {
    const maxStrength = Math.max(1, ...s.players.map(p => p.combat_strength || 0));
    cfEl.innerHTML = `
      <div class="cf-name">⚔ ${conflict.name} <span style="font-size:9px;color:var(--text-dim)">(Level ${conflict.level})</span></div>
      <div class="cf-rewards">${renderConflictRewards(conflict.rewards)}</div>
    `;
  } else {
    cfEl.innerHTML = `<div style="color:var(--text-dim);font-size:10px">No active conflict</div>`;
  }

  const cpDiv = document.getElementById("combat-players");
  cpDiv.innerHTML = "";
  const maxStr = Math.max(1, ...s.players.map(p => p.combat_strength || 0));
  s.players.forEach((p, i) => {
    const row = el("div","combat-player-row");
    const str = p.combat_strength || 0;
    const pct = Math.min(100, Math.round(str / maxStr * 100));
    row.innerHTML = `
      <div class="cp-name" style="color:var(--${G.playerColors[i]})">${shortName(p.name)}</div>
      <div class="cp-troops">${p.troops_in_conflict} troops${p.sandworms_in_conflict > 0 ? " + "+p.sandworms_in_conflict+"🪱" : ""}</div>
      <div class="cp-strength">Strength: ${str}</div>
      <div class="strength-bar-track"><div class="strength-bar-fill" style="width:${pct}%;background:var(--${G.playerColors[i]})"></div></div>
    `;
    cpDiv.appendChild(row);
  });

  const garr = document.getElementById("garrisons");
  garr.innerHTML = "";
  s.players.forEach((p, i) => {
    const chip = el("div","garrison-chip");
    chip.innerHTML = `
      <div class="gc-name" style="color:var(--${G.playerColors[i]})">${shortName(p.name)}</div>
      <div class="gc-troops">${p.troops_in_garrison} 🏰 / ${p.troops_in_reserve} res.</div>
    `;
    garr.appendChild(chip);
  });
}

function renderConflictRewards(rewards) {
  if (!rewards) return "";
  return Object.entries(rewards).map(([rank, effects]) => {
    const rankLabel = rank === "1" ? "🥇" : rank === "2" ? "🥈" : "🥉";
    return `<div class="cf-reward-rank">${rankLabel} ${formatRewards(effects)}</div>`;
  }).join("");
}

// ─────────────── IMPERIUM ROW ───────────────
function renderImperiumRow(s) {
  const aa = s.available_actions || {};
  const inAcquisition = aa.phase === "acquisition";
  const persuasion = aa.persuasion_left || 0;

  const rowEl = document.getElementById("imperium-row");
  rowEl.innerHTML = "";
  (s.board?.imperium_row || []).forEach(c => {
    const div = buildCard(c, "row-card", inAcquisition, persuasion);
    if (inAcquisition) {
      div.addEventListener("click", () => tryAcquireCard(c, "row"));
    }
    rowEl.appendChild(div);
  });

  const resEl = document.getElementById("reserve-piles");
  resEl.innerHTML = "";
  const rp = aa.reserve_prepare || s.board?.reserve_prepare_the_way;
  const rs = aa.reserve_spice   || s.board?.reserve_spice_must_flow;

  if (rp?.card || rp?.top) {
    const card = rp.card || rp.top;
    const rem  = rp.remaining || 0;
    const div = buildCard(card, "row-card", inAcquisition, persuasion);
    const extra = el("div","sp-spice-bonus"); extra.textContent = `×${rem} left`;
    div.appendChild(extra);
    if (inAcquisition) div.addEventListener("click", () => tryAcquireCard(card, "reserve"));
    resEl.appendChild(div);
  }
  if (rs?.card || rs?.top) {
    const card = rs.card || rs.top;
    const rem  = rs.remaining || 0;
    const div = buildCard(card, "row-card", inAcquisition, persuasion);
    const extra = el("div","sp-spice-bonus"); extra.textContent = `×${rem} left`;
    div.appendChild(extra);
    if (inAcquisition) div.addEventListener("click", () => tryAcquireCard(card, "reserve"));
    resEl.appendChild(div);
  }
}

// ─────────────── PLAYER AREA ────────────────
function renderPlayerArea(s) {
  const human = s.players.find(p => p.player_id === s.viewer_player_id);
  if (!human) return;

  const aa = s.available_actions || {};
  const inAcquisition = aa.phase === "acquisition";
  const persuasion = aa.persuasion_left || 0;

  // Hand label
  document.getElementById("your-name-label").textContent =
    (human.name || "Player").toUpperCase() + " — HAND";

  // Persuasion badge
  const pbadge = document.getElementById("persuasion-display");
  if (inAcquisition) {
    pbadge.classList.remove("hidden");
    pbadge.textContent = `🟢 ${persuasion} persuasion`;
  } else {
    pbadge.classList.add("hidden");
  }

  // Hand cards
  const handEl = document.getElementById("hand-cards");
  handEl.innerHTML = "";
  (human.hand || []).forEach(c => {
    const div = buildCard(c, "hand-card", false, 0);

    if (aa.phase === "agent_turn") {
      // Find this card's valid locations
      const entry = (aa.playable_cards || []).find(e => e.card_id === c.id);
      if (entry && entry.valid_location_ids.length > 0) {
        div.classList.add("selectable");
        div.addEventListener("click", () => selectCard(c, entry.valid_location_ids));
      } else {
        div.style.opacity = ".5";
      }
    }
    handEl.appendChild(div);
  });

  // Intrigue count badge
  document.getElementById("intrigue-count").textContent = human.intrigue_count || 0;

  // Intrigue cards
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
    chip.innerHTML = `
      <div class="ac-name">${c.name}</div>
      <div class="ac-cond">${contractCondition(c)}</div>
    `;
    acEl.appendChild(chip);
  });

  // Discard pile buttons for ALL players
  const discardStrip = document.getElementById("discard-piles-strip");
  discardStrip.innerHTML = "";
  s.players.forEach((p, i) => {
    if (!p.discard_size) return;
    const btn = el("button","discard-pile-btn");
    btn.textContent = `${shortName(p.name)} (${p.discard_size})`;
    btn.style.borderColor = `var(--${G.playerColors[i]})`;
    btn.addEventListener("click", () => showDiscard(p, s));
    discardStrip.appendChild(btn);
  });
}

// ─────────────── ACTION BUTTONS ─────────────
function updateActionButtons(s) {
  const aa = s.available_actions || {};
  const revealBtn = document.getElementById("reveal-btn");
  const endAcqBtn = document.getElementById("end-acq-btn");

  revealBtn.classList.toggle("hidden", aa.phase !== "agent_turn");
  endAcqBtn.classList.toggle("hidden", aa.phase !== "acquisition");
}

document.getElementById("reveal-btn").addEventListener("click", () => {
  postAction({ type: "reveal" });
  clearSelectedCard();
});

function endAcquisition() { postAction({ type: "end_acquisition" }); }

// ─────────────── CARD CLICK FLOW ────────────
function selectCard(card, validLocations) {
  if (G.selectedCard?.id === card.id) {
    clearSelectedCard();
    return;
  }
  G.selectedCard = { id: card.id, validLocations };
  // Refresh highlight
  render();
}

function clearSelectedCard() {
  G.selectedCard = null;
  render();
}

function placeAgent(cardId, locationId) {
  postAction({ type: "place_agent", card_id: cardId, location_id: String(locationId), troops: 0 });
  clearSelectedCard();
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
  const aa = G.state?.available_actions || {};
  if (aa.phase !== "acquisition") {
    showError("Contracts can only be accepted during the acquisition phase"); return;
  }
  postAction({ type: "acquire_contract", contract_id: String(contract.id) });
}

// ─────────────── CHOICE MODAL ───────────────
function showChoiceModal(choice) {
  const modal = document.getElementById("choice-modal");
  const titleEl = document.getElementById("choice-title");
  const descEl = document.getElementById("choice-desc");
  const optionsEl = document.getElementById("choice-options");
  optionsEl.innerHTML = "";

  const ctype = choice.type;
  titleEl.textContent = choiceTitle(ctype);
  descEl.textContent  = choice.description || "";

  const items = getChoiceItems(choice);
  items.forEach(item => {
    const btn = el("button", "choice-btn" + (item.disabled ? " disabled" : ""));
    btn.textContent = item.label;
    if (!item.disabled) {
      btn.addEventListener("click", () => {
        modal.classList.add("hidden");
        postAction({ type: "resolve_choice", option_id: item.value });
      });
    }
    optionsEl.appendChild(btn);
  });

  modal.classList.remove("hidden");
}

function choiceTitle(ctype) {
  const map = {
    choice: "Choose an option",
    spy_post: "Place Spy",
    play_spy: "Play Spy",
    influence_faction: "Choose Faction",
    conditional: "Optional: Pay for Bonus?",
    trash_card: "Trash a Card",
    trash_to_acquire: "Trash a Card to Unlock Acquisition",
    discard_card: "Discard a Card",
    steal_intrigue: "Steal Intrigue From",
    recall_agent: "Recall Agent From",
    accept_contract: "Accept a Contract",
    acquire_card: "Acquire Card (Free)",
    choose_opponent_discard: "Force Opponent to Discard",
    play_spy_on_space: "Plant Spy on Space",
    conditional_multi_choice: "Optional Bonuses",
    reveal_passive_choice: "Leader Passive Ability",
  };
  return map[ctype] || "Make a Choice";
}

function getChoiceItems(choice) {
  const ctype = choice.type;

  if (ctype === "choice") {
    return (choice.options || []).map(o => ({
      label: o.label || o.id, value: o.id,
      disabled: o.available === false,
    }));
  }
  if (ctype === "influence_faction") {
    return (choice.factions || []).map(f => ({ label: factionLabel(f), value: f }));
  }
  if (ctype === "conditional") {
    const costs   = formatRewards(choice.costs || []);
    const rewards = formatRewards(choice.rewards || []);
    return [
      { label: `✓ Pay ${costs} → gain ${rewards}`, value: "accept" },
      { label: "✗ Skip", value: "decline" },
    ];
  }
  if (ctype === "trash_card" || ctype === "discard_card" || ctype === "trash_to_acquire") {
    return (choice.available_cards || []).map(item => {
      const c = item.card || item;
      return { label: `${c.name} (from ${item.source || "hand"})`, value: c.id };
    });
  }
  if (ctype === "accept_contract") {
    return (choice.available_contracts || []).map(c => ({
      label: `${c.name} — ${contractCondition(c)} → ${formatRewards(c.rewards||[])}`,
      value: c.id,
    }));
  }
  if (ctype === "steal_intrigue" || ctype === "choose_opponent_discard") {
    return (choice.valid_targets || []).map(t => ({
      label: `${t.player_name} (${t.intrigue_count ?? t.hand_size} cards)`,
      value: t.player_id,
    }));
  }
  if (ctype === "recall_agent") {
    const spaces = G.state?.board?.spaces || [];
    return (choice.placed_locations || []).map(lid => {
      const sp = spaces.find(s => String(s.id) === String(lid));
      return { label: sp?.name || String(lid), value: String(lid) };
    });
  }
  if (ctype === "spy_post" || ctype === "play_spy") {
    return (choice.available_posts || []).map(p => ({
      label: p.post_name || p.post_id || p,
      value: p.post_id || p,
    }));
  }
  if (ctype === "play_spy_on_space") {
    return (choice.eligible_spaces || []).map(sp => ({
      label: sp.space_name || sp.space_id, value: sp.space_id,
    }));
  }
  if (ctype === "conditional_multi_choice") {
    return (choice.options || []).map(o => ({
      label: o.label || o.id, value: o.id,
    }));
  }
  if (ctype === "reveal_passive_choice") {
    return (choice.options || []).map(o => ({
      label: o.description || o.id, value: o.id,
    }));
  }
  if (ctype === "acquire_card") {
    const row = G.state?.board?.imperium_row || [];
    const target = choice.card;
    const cards = target ? row.filter(c => c.name === target) : row;
    return cards.map(c => ({ label: `${c.name} (cost ${c.cost})`, value: c.id }));
  }
  return [{ label: "OK", value: "ok" }];
}

function factionLabel(f) {
  return { fremen:"Fremen", bene_gesserit:"Bene Gesserit",
           spacing_guild:"Spacing Guild", emperor:"Emperor" }[f] || f;
}

// ─────────────── DISCARD MODAL ──────────────
function showDiscard(player, s) {
  const modal = document.getElementById("discard-modal");
  document.getElementById("discard-title").textContent =
    `${player.name}'s Discard Pile (${player.discard_size} cards)`;
  const cardsEl = document.getElementById("discard-cards");
  cardsEl.innerHTML = "";

  // If it's our own discard we have the cards; otherwise just show count
  const cards = player.discard || [];
  if (cards.length) {
    cards.forEach(c => cardsEl.appendChild(buildCard(c, "row-card", false, 0)));
  } else {
    cardsEl.innerHTML = `<div style="color:var(--text-dim);padding:12px">
      (Card details not visible for opponents)</div>`;
  }
  modal.classList.remove("hidden");
}

function closeDiscard() {
  document.getElementById("discard-modal").classList.add("hidden");
}

// ─────────────── CARD BUILDER ───────────────
function buildCard(card, extraClass, inAcquisition, persuasion) {
  const div = el("div", `card ${extraClass}`);

  const faction = card.factions?.[0] || "neutral";
  const affordable = !inAcquisition || card.cost <= persuasion;
  if (inAcquisition) div.classList.add(affordable ? "affordable acquisition-card" : "unaffordable");

  // Header
  const hdr = el("div", `card-header ${faction}`);
  const nameEl = el("span","card-name"); nameEl.textContent = card.name;
  hdr.appendChild(nameEl);
  if (card.cost > 0) {
    const costEl = el("span","card-cost"); costEl.textContent = card.cost;
    hdr.appendChild(costEl);
  } else if (inAcquisition) {
    const costEl = el("span","card-cost free"); costEl.textContent = "0";
    hdr.appendChild(costEl);
  }
  div.appendChild(hdr);

  // Body
  const body = el("div","card-body");

  // Agent icons
  const icons = card.agent_icons || [];
  if (icons.length) {
    const iconRow = el("div","card-icons");
    icons.forEach(ic => {
      const pip = el("span", `icon-pip ${ic}`);
      pip.textContent = agentIconLabel(ic);
      iconRow.appendChild(pip);
    });
    body.appendChild(iconRow);
  }

  // Faction tags
  if (card.factions && card.factions.length) {
    const facRow = el("div","card-factions");
    card.factions.forEach(f => {
      const tag = el("span",`icon-pip ${f}`);
      tag.textContent = factionLabel(f);
      facRow.appendChild(tag);
    });
    body.appendChild(facRow);
  }

  // Agent effects
  const agEff = card.agent_effects || [];
  if (agEff.length) {
    const lbl = el("div","card-section-label"); lbl.textContent = "AGENT"; body.appendChild(lbl);
    const efDiv = el("div","card-effects");
    agEff.forEach(e => efDiv.appendChild(effectLine(e)));
    body.appendChild(efDiv);
  }

  // Reveal effects
  const rvEff = card.reveal_effects || [];
  if (rvEff.length) {
    const lbl = el("div","card-section-label"); lbl.textContent = "REVEAL"; body.appendChild(lbl);
    const efDiv = el("div","card-effects");
    rvEff.forEach(e => efDiv.appendChild(effectLine(e)));
    body.appendChild(efDiv);
  }

  // On-acquire effects
  const acqEff = card.on_acquire_effects || [];
  if (acqEff.length) {
    const lbl = el("div","card-section-label"); lbl.textContent = "ON BUY"; body.appendChild(lbl);
    const efDiv = el("div","card-effects");
    acqEff.forEach(e => efDiv.appendChild(effectLine(e)));
    body.appendChild(efDiv);
  }

  div.appendChild(body);
  return div;
}

function buildIntrigueCard(card, isAgentPhase) {
  const div = el("div","card intrigue-card");
  const hdr = el("div","card-header");
  const nameEl = el("span","card-name"); nameEl.textContent = card.name;
  hdr.appendChild(nameEl);
  const phaseTag = el("span","intrigue-phase");
  phaseTag.textContent = (card.phases || []).map(p => p).join("/") || "Plot";
  hdr.appendChild(phaseTag);
  div.appendChild(hdr);

  const body = el("div","card-body");
  const effects = card.effects || [];
  if (effects.length) {
    const efDiv = el("div","card-effects");
    effects.slice(0,3).forEach(e => efDiv.appendChild(effectLine(e)));
    body.appendChild(efDiv);
  }
  div.appendChild(body);

  if (isAgentPhase) {
    div.addEventListener("click", () => {
      postAction({ type: "play_intrigue", card_id: card.id });
    });
  }
  return div;
}

// ─────────────── EFFECT FORMATTING ──────────
function effectLine(e) {
  const line = el("div","effect-line");
  const bullet = el("span","ef-bullet"); bullet.textContent = "•";
  const text = el("span","ef-gain");   text.textContent = describeEffect(e);
  line.appendChild(bullet); line.appendChild(text);
  if (e.type === "choice" || e.type === "conditional") line.classList.add("choice-effect");
  return line;
}

function describeEffect(e) {
  if (!e || typeof e !== "object") return String(e || "");
  const t = e.type || "";
  const amt = e.amount || 1;

  if (t === "resource") {
    const icons = { solari:"🪙", spice:"🌶", water:"💧", troop:"🗡", persuasion:"🗣", sword:"⚔", worm:"🪱", agent:"📍", victory_point:"⭐" };
    return `+${amt} ${icons[e.resource] || e.resource}`;
  }
  if (t === "draw")       return `Draw ${amt} ${e.deck === "intrigue" ? "🃏" : "📄"}`;
  if (t === "influence")  return `+${amt} ${factionLabel(e.target)} inf.`;
  if (t === "victory_point") return `+${amt} ⭐`;
  if (t === "choice")     return choiceSummary(e);
  if (t === "conditional") return `Optional: pay for bonus`;
  if (t === "trash")      return `Trash ${amt} card(s)`;
  if (t === "restrict")   return `Restrict: ${e.restriction || ""}`;
  if (t === "accept")     return "Accept contract";
  if (t === "council_seat") return "High Council seat";
  if (t === "shieldwall_deactivate") return "Destroy shield wall";
  if (t === "maker_hooks") return "Maker hooks";
  if (t === "endgame_condition") return `End-game: ${e.condition || ""}`;
  return t;
}

function choiceSummary(e) {
  const opts = (e.options || []).map(o => {
    if (o.reward) return formatRewards(o.reward);
    if (o.id) return o.id;
    return "";
  }).filter(Boolean);
  return "Choose: " + opts.slice(0,2).join(" or ") + (opts.length > 2 ? "…" : "");
}

function formatRewards(effects) {
  if (!Array.isArray(effects)) return String(effects || "");
  return effects.map(describeEffect).filter(Boolean).join(", ") || "—";
}

// ─────────────── EVENT LOG ──────────────────
function appendEvents(events) {
  const logEl = document.getElementById("event-log");
  events.forEach(ev => {
    const div = el("div", `ev ev-${evClass(ev.type)}`);
    div.textContent = describeEvent(ev);
    logEl.appendChild(div);
    while (logEl.children.length > 60) logEl.removeChild(logEl.firstChild);
  });
  logEl.scrollTop = logEl.scrollHeight;
}

function evClass(t) {
  if (["combat_resolved","deploy_troops"].includes(t)) return "combat";
  if (["acquire_card","acquire_contract"].includes(t)) return "acquire";
  if (["reveal","auto_reveal"].includes(t)) return "reveal";
  if (["contract_completed"].includes(t)) return "contract";
  if (["new_round"].includes(t)) return "round";
  return "";
}

function describeEvent(ev) {
  const t = ev.type;
  if (t === "place_agent")    return `${ev.player} → ${ev.location} (${ev.card})`;
  if (t === "reveal")         return `${ev.player} reveals (${ev.persuasion} persuasion)`;
  if (t === "auto_reveal")    return `${ev.player} auto-reveals (${ev.persuasion} persuasion)`;
  if (t === "acquire_card")   return `${ev.player} buys ${ev.card} (${ev.cost})`;
  if (t === "acquire_contract") return `${ev.player} takes contract${ev.completed ? " ✓" : ""}`;
  if (t === "play_intrigue")  return `${ev.player} plays ${ev.card} (intrigue)`;
  if (t === "combat_resolved") return `⚔ ${ev.winner} wins ${ev.conflict}`;
  if (t === "contract_completed") return `🎉 ${ev.player}: ${ev.contract} complete!`;
  if (t === "recall")         return `${ev.player} recalls agents`;
  if (t === "new_round")      return `═══ Round ${ev.round} ═══`;
  if (t === "new_conflict")   return `Conflict: ${ev.conflict}`;
  return `${t}: ${JSON.stringify(ev).slice(0,40)}`;
}

// ─────────────── UTILITIES ──────────────────
function el(tag, className) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  return e;
}

function shortName(name) {
  return name?.length > 8 ? name.slice(0,7) + "…" : (name || "?");
}

function showError(msg) {
  // Flash a temporary toast error
  const toast = el("div", "choice-btn disabled");
  toast.style.cssText = "position:fixed;top:10px;right:10px;z-index:9999;max-width:300px;background:#3a1010;border:1px solid #e06060;color:#f08080;padding:10px";
  toast.textContent = "⚠ " + msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function showFullState() {
  if (!G.state) return;
  const human = G.state.players.find(p => p.player_id === G.state.viewer_player_id);
  if (!human) return;
  alert(`Your stats:\nVP: ${human.victory_points} | Solari: ${human.solari} | Spice: ${human.spice} | Water: ${human.water}\nTroops: ${human.troops_in_garrison} garrison / ${human.troops_in_conflict} conflict\nAgents: ${human.agents_available}/${human.total_available_agents}\nSpies: ${human.spies_available}/${human.total_available_spies}\nInfluence — Fr:${human.influence?.fremen} BG:${human.influence?.bene_gesserit} GU:${human.influence?.spacing_guild} EM:${human.influence?.emperor}`);
}
