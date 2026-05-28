"""Aggressive game fuzzer: many games, both player counts, varied leaders,
heavy intrigue/contract/reserve usage. Catches both error-fields and raw
exceptions. Reports unique failures with traceback."""
import sys, random, traceback, collections
sys.path.insert(0, '.')
from ui.game_session import GameSession

LEADERS = [1, 2, 3, 4, 5, 7, 8, 9]  # exclude Muad'Dib(6) randomly-included anyway


def pick_option(pc):
    ctype = pc.get('type', '')
    opts = pc.get('options', [])
    if opts:
        valid = [o for o in opts if o.get('available', True) is not False]
        pool = valid or opts
        return str(random.choice(pool)['id'])
    if ctype in ('trash_card', 'discard_card', 'trash_to_acquire'):
        cards = pc.get('available_cards', [])
        if cards:
            c = random.choice(cards)
            card = c.get('card', c)
            return str(card.get('id', ''))
    if ctype == 'influence_faction':
        f = pc.get('factions', [])
        return random.choice(f) if f else 'fremen'
    if ctype == 'conditional':
        return random.choice(['accept', 'decline'])
    if ctype == 'accept_contract':
        contracts = pc.get('available_contracts', [])
        if contracts and random.random() < 0.7:
            return str(random.choice(contracts)['id'])
        return 'skip'
    if ctype in ('steal_intrigue', 'choose_opponent_discard'):
        t = pc.get('valid_targets', [])
        return t[0]['player_id'] if t else 'p1'
    if ctype == 'recall_agent':
        locs = pc.get('placed_locations', [])
        return str(locs[0]) if locs else '1'
    if ctype in ('spy_post', 'play_spy'):
        posts = pc.get('available_posts', [])
        if posts:
            p = posts[0]
            return str(p.get('post_id', p) if isinstance(p, dict) else p)
        return 'ok'
    if ctype == 'play_spy_on_space':
        s = pc.get('eligible_spaces', [])
        return str(s[0]['space_id']) if s else 'ok'
    if ctype == 'conditional_multi_choice' or ctype == 'reveal_passive_choice':
        o = pc.get('options', [])
        return str(o[0]['id']) if o else 'ok'
    return 'ok'


def run_game(seed, pcount):
    random.seed(seed)
    human_leader = random.choice(LEADERS)
    session = GameSession.new(player_count=pcount, human_name='Human',
                              selected_leaders=[human_leader])
    errors = []
    for step in range(5000):
        snap = session.snapshot()
        s = snap['state']
        aa = s.get('available_actions', {})
        phase = aa.get('phase', s.get('phase', ''))
        if s.get('game_over'):
            return errors, step, 'game_over'

        pc = snap.get('pending_choice')
        if isinstance(pc, dict):
            chosen = pick_option(pc)
            r = session.execute_action({'type': 'resolve_choice', 'option_id': chosen})
            if r.get('error'):
                errors.append(f'resolve_choice({pc.get("type")}) chosen={chosen!r}: {r["error"]}')
            continue

        ptd = snap.get('pending_troop_deployment')
        if ptd:
            r = session.execute_action({'type': 'deploy_troops',
                                        'troops': random.randint(0, ptd.get('max_troops', 0))})
            if r.get('error'):
                errors.append(f'deploy_troops: {r["error"]}')
            continue

        if phase == 'agent_turn':
            playable = aa.get('playable_cards', [])
            if playable and random.random() < 0.7:
                card = random.choice(playable)
                locs = card.get('valid_location_ids', [])
                if locs:
                    r = session.execute_action({'type': 'place_agent',
                                                'card_id': card['card_id'],
                                                'location_id': random.choice(locs)})
                    if r.get('error'):
                        errors.append(f'place_agent: {r["error"]}')
                    continue
            r = session.execute_action({'type': 'reveal'})
            if r.get('error'):
                errors.append(f'reveal: {r["error"]}')
        elif phase == 'acquisition':
            # try contract accept
            if aa.get('can_accept_contract') and random.random() < 0.5:
                crow = aa.get('contract_row', [])
                if crow:
                    r = session.execute_action({'type': 'acquire_contract',
                                                'contract_id': str(crow[0]['id'])})
                    if r.get('error') and 'trigger' not in r['error'].lower():
                        errors.append(f'acquire_contract: {r["error"]}')
                    continue
            imperium = aa.get('imperium_row', [])
            persuasion = aa.get('persuasion_left', 0)
            affordable = [c for c in imperium if c.get('cost', 999) <= persuasion]
            # reserves
            for key, src in (('reserve_prepare', 'prepare'), ('reserve_spice', 'spice')):
                rv = aa.get(key)
                if rv and rv.get('card', {}).get('cost', 999) <= persuasion:
                    affordable.append({'id': rv['card']['id']})
            if affordable and random.random() < 0.6:
                c = random.choice(affordable)
                r = session.execute_action({'type': 'acquire_card', 'card_id': c['id']})
                if r.get('error'):
                    errors.append(f'acquire_card: {r["error"]}')
            else:
                r = session.execute_action({'type': 'end_acquisition'})
                if r.get('error'):
                    errors.append(f'end_acquisition: {r["error"]}')
        else:
            errors.append(f'UNEXPECTED_PHASE: {phase!r}')
            return errors, step, 'stuck'
    return errors, 5000, 'limit'


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    error_counter = collections.Counter()
    crash_counter = collections.Counter()
    completed = 0
    not_completed = 0
    for i in range(n):
        pcount = random.choice([3, 4]) if i % 2 == 0 else (3 if i % 4 == 1 else 4)
        seed = i * 31 + 11
        try:
            errs, steps, status = run_game(seed, pcount)
            if status == 'game_over':
                completed += 1
            else:
                not_completed += 1
                error_counter[f'[{status}] seed={seed} p{pcount} steps={steps}'] += 1
            for e in errs:
                # normalize numbers out for grouping
                import re
                key = re.sub(r'\d+', 'N', e)
                error_counter[key] += 1
        except Exception as e:
            tb = traceback.format_exc()
            # last frame
            lines = tb.strip().split('\n')
            key = f'{type(e).__name__}: {e} @ {lines[-2].strip() if len(lines)>=2 else "?"}'
            crash_counter[key] += 1
            if crash_counter[key] <= 1:
                print(f'--- CRASH seed={seed} p{pcount} ---')
                print(tb[-1500:])
    print(f'\n=== {n} games: {completed} completed, {not_completed} not-completed ===')
    print(f'\nError-field groups ({len(error_counter)}):')
    for k, v in error_counter.most_common(25):
        print(f'  x{v}: {k}')
    print(f'\nException groups ({len(crash_counter)}):')
    for k, v in crash_counter.most_common(25):
        print(f'  x{v}: {k}')


if __name__ == '__main__':
    main()
