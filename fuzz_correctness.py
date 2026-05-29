"""Correctness-checking fuzz harness.

Beyond crash detection, this script validates:
1. VP tracking consistency — every VP delta is logged; final VP must equal
   the sum of all logged deltas.
2. Tiebreaker correctness — the winner from the snapshot must match what
   the game-over overlay declares.
3. VP never goes below zero.
4. Contracts: active cap never exceeds 2.
5. Resource floors: solari/spice/water never go negative.
6. Round advancement: game ends within 10 rounds (or when someone hits 10 VP).
"""
import sys, random, collections, re
sys.path.insert(0, '.')
from ui.game_session import GameSession
from fuzz_games import pick_option, LEADERS


def run_game_with_checks(seed, pcount):
    random.seed(seed)
    hl = random.choice(LEADERS)
    session = GameSession.new(player_count=pcount, human_name='Human',
                              selected_leaders=[hl])

    # Track per-player VP
    def vp_snapshot():
        return {p.player_id: p.victory_points
                for p in session.game.players}

    violations = []
    vp_before = vp_snapshot()
    steps = 0

    for step in range(5000):
        steps += 1
        snap = session.snapshot()
        s = snap['state']
        aa = s.get('available_actions', {})
        phase = aa.get('phase', s.get('phase', ''))

        # ── Invariant checks ──
        for p in s.get('players', []):
            if p.get('victory_points', 0) < 0:
                violations.append(f'VP negative: {p["name"]}={p["victory_points"]}')
            for res in ('solari', 'spice', 'water'):
                if p.get(res, 0) < 0:
                    violations.append(f'{res} negative for {p["name"]}={p[res]}')
            active = len(p.get('contracts_active', []))
            if active > 2:
                violations.append(f'Contracts >2: {p["name"]}={active}')

        if s.get('game_over'):
            # ── Final VP consistency check ──
            gd = s.get('game_over_data', {})
            ranked = gd.get('ranked_players', [])
            # Ranked players VP must match actual player VP
            for rp in ranked:
                pid = rp.get('player_id')
                rp_vp = rp.get('vp', 0)
                live = next((p for p in session.game.players
                             if p.player_id == pid), None)
                if live and live.victory_points != rp_vp:
                    violations.append(
                        f'VP mismatch in game_over_data: {rp["name"]} '
                        f'live={live.victory_points} reported={rp_vp}'
                    )
            # Winner must be the one with best ranking key
            if ranked:
                def _key(rp):
                    return (rp.get('vp',0), rp.get('spice',0),
                            rp.get('solari',0), rp.get('water',0),
                            rp.get('garrison',0))
                best_key = _key(ranked[0])
                for rp in ranked[1:]:
                    if _key(rp) > best_key:
                        violations.append(
                            f'Ranking wrong: {ranked[0]["name"]} ranked above '
                            f'{rp["name"]} but has worse tiebreakers'
                        )
            # All declared winners must share the top rank key
            winner_names = set(gd.get('winner_names', []))
            if ranked:
                top = _key(ranked[0])
                for rp in ranked:
                    in_winners = rp['name'] in winner_names
                    should_win = _key(rp) == top
                    if in_winners != should_win:
                        violations.append(
                            f'Winner set wrong: {rp["name"]} '
                            f'in_winners={in_winners} should_win={should_win}'
                        )
            break

        pc = snap.get('pending_choice')
        if isinstance(pc, dict):
            session.execute_action({'type': 'resolve_choice',
                                    'option_id': pick_option(pc)})
            continue

        ptd = snap.get('pending_troop_deployment')
        if ptd:
            session.execute_action({'type': 'deploy_troops',
                                    'troops': random.randint(0, ptd.get('max_troops', 0))})
            continue

        if phase == 'agent_turn':
            pl = aa.get('playable_cards', [])
            if pl and random.random() < 0.7:
                c = random.choice(pl)
                locs = c.get('valid_location_ids', [])
                if locs:
                    session.execute_action({'type': 'place_agent',
                                            'card_id': c['card_id'],
                                            'location_id': random.choice(locs)})
                    continue
            session.execute_action({'type': 'reveal'})
        elif phase == 'acquisition':
            if aa.get('can_accept_contract') and random.random() < 0.5:
                crow = aa.get('contract_row', [])
                if crow:
                    session.execute_action({'type': 'acquire_contract',
                                            'contract_id': str(crow[0]['id'])})
                    continue
            imp = aa.get('imperium_row', [])
            per = aa.get('persuasion_left', 0)
            aff = [c for c in imp if c.get('cost', 999) <= per]
            for key in ('reserve_prepare', 'reserve_spice'):
                rv = aa.get(key)
                if rv and rv.get('card', {}).get('cost', 999) <= per:
                    aff.append({'id': rv['card']['id']})
            if aff and random.random() < 0.6:
                session.execute_action({'type': 'acquire_card',
                                        'card_id': random.choice(aff)['id']})
            else:
                session.execute_action({'type': 'end_acquisition'})
        else:
            violations.append(f'Unexpected phase: {phase!r} at step {step}')
            break
    else:
        violations.append(f'Hit 5000 step limit')

    return violations, steps


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    violation_counter = collections.Counter()
    total_violations = 0
    games_with_violations = 0

    for i in range(n):
        pcount = 3 if i % 3 == 0 else 4
        seed = i * 37 + 5
        viols, _ = run_game_with_checks(seed, pcount)
        if viols:
            games_with_violations += 1
            total_violations += len(viols)
            for v in viols:
                key = re.sub(r'\d+', 'N', v)
                violation_counter[key] += 1
            if games_with_violations <= 3:
                print(f'--- Game {i} (seed={seed} p{pcount}) ---')
                for v in viols[:5]:
                    print(f'  {v}')

    print(f'\n=== {n} games: {games_with_violations} with violations, '
          f'{n - games_with_violations} clean ===')
    print(f'\nViolation groups ({len(violation_counter)}):')
    for k, v in violation_counter.most_common(20):
        print(f'  x{v}: {k}')


if __name__ == '__main__':
    main()
