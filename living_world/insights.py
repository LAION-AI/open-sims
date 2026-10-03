"""Read-only, bounded projections for the neighborhood's live insight overlay.

The dashboard reports accepted simulation state and ledger beats, never inferred
private stories or invented event counts. It does not advance the world.
"""
from collections import Counter, defaultdict

from . import affect


def _stage(age):
    return 'child' if age < 13 else 'teen' if age < 18 else 'elder' if age >= 66 else 'adult'


def _event_kind(beat):
    rule = beat.get('rule_id', '').lower()
    words = (rule + ' ' + beat.get('narration', '')).lower()
    if any(word in words for word in ('sabotage', 'undermine', 'gossip', 'rumor', 'blackmail')):
        return 'intrigue'
    if any(word in words for word in ('argument', 'quarrel', 'fight', 'rival', 'conflict', 'fired')):
        return 'drama'
    if any(word in words for word in ('romance', 'flirt', 'kiss', 'love', 'date', 'affection')):
        return 'romance'
    if any(word in words for word in ('party', 'event', 'celebrat', 'gather')):
        return 'event'
    if any(word in words for word in ('social', 'chat', 'coworker', 'friend', 'help')):
        return 'social'
    if any(word in words for word in ('work', 'career', 'hire', 'job', 'profession')):
        return 'career'
    return 'life'


def build_world_insights(world):
    actors = list(world.actors.values())
    names = {actor['id']: actor['name'] for actor in actors}
    stages = Counter()
    moods = Counter()
    stage_moods = defaultdict(Counter)
    jobs = Counter()
    stage_wellbeing = defaultdict(list)
    occupants = defaultdict(list)
    active = []
    ambitions = []
    buildings = list(world.spatial.buildings)
    for actor in actors:
        stage = _stage(actor['age'])
        stages[stage] += 1
        job = actor.get('career', {}).get('job') or actor.get('profile', {}).get('job') or 'Unassigned'
        jobs[job] += 1
        wellbeing = 1 - sum(world.needs_at(actor).values()) / max(len(actor['needs']), 1)
        stage_wellbeing[stage].append(wellbeing)
        projection = affect.project_affect(actor, world.now)
        primary = projection.get('primary') or {}
        if isinstance(primary, str):
            primary = {'id': primary}
        mood = primary.get('label_de') or primary.get('label') or primary.get('id') or actor.get('emotion', {}).get('type') or 'Neutral'
        moods[mood] += 1
        stage_moods[stage][mood] += 1
        pos = world.position_at(actor)
        building = next((b for b in buildings if b['x'] <= pos[0] < b['x'] + b['w']
                         and b['y'] <= pos[1] < b['y'] + b['h']), None)
        if building:
            occupants[building['id']].append({'id': actor['id'], 'name': actor['name'], 'stage': stage})
        action = actor.get('action') or {}
        if action and (action.get('kind') in {'chat', 'flirt', 'kiss', 'party', 'argue', 'fight'}
                       or action.get('social_category')):
            target = action.get('target_id')
            active.append({'id': actor['id'], 'name': actor['name'], 'target_id': target if target in names else None,
                           'target_name': names.get(target), 'kind': action.get('kind'),
                           'label': action.get('label') or action.get('kind'),
                           'social_category': action.get('social_category'),
                           'building': building['name'] if building else 'Outdoors'})
        for ambition in actor.get('psychology', {}).get('ambitions', []):
            if not ambition.get('completed'):
                ambitions.append({'id': actor['id'], 'name': actor['name'],
                                  'title': ambition.get('title', 'Ambition'),
                                  'progress': round(float(ambition.get('progress', 0)), 3)})
    ties = []
    seen = set()
    counts = Counter()
    for actor in actors:
        for other_id, relation in actor.get('relations', {}).items():
            if other_id not in names or other_id == actor['id']:
                continue
            pair = tuple(sorted((actor['id'], other_id)))
            if pair in seen:
                continue
            seen.add(pair)
            reverse = world.actors[other_id].get('relations', {}).get(actor['id'], {})
            layers = relation.get('layers', {})
            family = actor.get('family', {})
            other_family = world.actors[other_id].get('family', {})
            kinds = []
            if (other_id in family.get('parent_ids', []) or actor['id'] in other_family.get('parent_ids', [])
                    or other_id in family.get('known_kin_ids', [])):
                kinds.append('family')
            if family.get('partner_id') == other_id or layers.get('romance', {}).get('status') not in (None, 'none'):
                kinds.append('romance')
            if relation.get('closeness', 0) >= .55 and not kinds:
                kinds.append('friendship')
            if relation.get('tension', 0) >= .5 or relation.get('rivalry', 0) >= .5:
                kinds.append('rivalry')
            if layers.get('coworker', {}).get('status') not in (None, 'none'):
                kinds.append('coworker')
            for kind in kinds:
                counts[kind] += 1
            if kinds:
                ties.append({'a': pair[0], 'b': pair[1], 'a_name': names[pair[0]], 'b_name': names[pair[1]],
                             'kinds': kinds,
                             'closeness': round((relation.get('closeness', 0) + reverse.get('closeness', 0)) / 2, 2),
                             'tension': round(max(relation.get('tension', 0), reverse.get('tension', 0)), 2)})
    beats = world.store.recent(limit=100)
    events = [{'id': b['id'], 'at': b['interval'][1], 'kind': _event_kind(b),
               'text': b.get('narration', ''),
               'participants': [{'id': aid, 'name': names[aid]} for aid in b.get('participants', []) if aid in names]}
              for b in beats if b.get('rule_id') != 'initialization']
    return {'clock': world.now, 'population': len(actors), 'households': len(world.spatial.households),
            'wellbeing': round(sum(sum(values) for values in stage_wellbeing.values()) / max(len(actors), 1), 3),
            'demographics': [{'stage': stage, 'count': stages[stage],
                              'wellbeing': round(sum(stage_wellbeing[stage]) / max(len(stage_wellbeing[stage]), 1), 3),
                              'moods': [{'name': name, 'count': count}
                                        for name, count in stage_moods[stage].most_common(3)]}
                             for stage in ('child', 'teen', 'adult', 'elder')],
            'moods': [{'name': name, 'count': count} for name, count in moods.most_common()],
            'professions': [{'name': name, 'count': count} for name, count in jobs.most_common()],
            'buildings': [{'id': b['id'], 'name': b['name'], 'occupants': occupants[b['id']]}
                          for b in buildings if occupants[b['id']]],
            'active_social': active[:30], 'relationship_counts': dict(counts),
            'relationships': sorted(ties, key=lambda tie: (-tie['tension'], -tie['closeness']))[:35],
            'ambitions': sorted(ambitions, key=lambda item: -item['progress'])[:24],
            'events': events[:50],
            'event_counts': dict(Counter(event['kind'] for event in events))}
