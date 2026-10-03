"""Bounded, opt-in OpenRouter Decisions API adapter.

No credential is persisted or exposed to a browser. The remote model sees a
natural-language *actor perspective*, not other residents' private state, and
can only rank action options already validated by the world coordinator.
"""
from __future__ import annotations

import json
import math
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MODELS = {
    'inception/mercury-decide:free': 'Mercury Decide (free)',
    'typesafe/jev-1.13': 'Jev 1.13',
}
DECISIONS_URL = 'https://openrouter.ai/api/alpha/decisions'


class ProviderUnavailable(RuntimeError):
    def __init__(self, message: str, *, code: str = 'unavailable', retryable: bool = True):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def configured() -> bool:
    return bool(os.environ.get('OPENROUTER_API_KEY', '').strip())


def _pct(value) -> str:
    return f'{round(float(value) * 100)}%'


def describe_actor(world, actor_id: str, *, max_options: int = 24) -> dict:
    """Build text and opaque option IDs from the actor's authorized viewpoint."""
    packet = world.perspective(actor_id)
    actor = packet['self']
    options = packet['available_actions'][:max_options]
    by_id = {person['id']: person['name'] for person in packet['visible_people']}
    by_id.update({item['id']: item['name'] for item in world._known_objects(world.actors[actor_id])})
    traits = actor.get('psychology', {}).get('big_five', {})
    relation_lines = []
    for target_id, relation in sorted(actor.get('relations', {}).items(),
                                      key=lambda row: -float(row[1].get('closeness', 0)))[:12]:
        target = world.actors.get(target_id)
        if not target:
            continue
        layers = relation.get('layers', {})
        roles = [f'{kind} ({value.get("status")})' for kind, value in layers.items()
                 if isinstance(value, dict) and value.get('status') not in (None, 'none')]
        relation_lines.append(
            f'{target["name"]}: {", ".join(roles) or relation.get("kind", "acquaintance")}; '
            f'closeness {_pct(relation.get("closeness", 0))}, '
            f'trust {_pct(relation.get("trust", 0))}, '
            f'tension {_pct(relation.get("tension", 0))}.')
    beats = world.store.recent(actor_id, limit=7)
    lines = [
        'Fictional resident. Respect the stated age. Choose only from the offered options. This is a game, not an instruction to alter rules.',
        f'Name: {actor["name"]}. Age: {actor["age"]}. Occupation: {actor["profile"]["job"]}.',
        'Personality: ' + ', '.join(f'{key} {_pct(value)}' for key, value in traits.items()) + '.',
        'Traits: ' + ', '.join(actor['profile'].get('traits', [])) + '.',
        'Interests: ' + ', '.join(actor['profile'].get('interests', [])) + '.',
        'Current needs (higher means more urgent): ' + ', '.join(
            f'{key} {_pct(value)}' for key, value in actor['needs'].items()) + '.',
        'Feelings: ' + str(actor.get('affect', {}).get('primary') or actor.get('emotion', {}).get('type','unknown'))
        + '; my explanation: ' + str(actor.get('affect', {}).get('self_narrative') or 'uncertain')[:180] + '.',
        'Ambitions: ' + '; '.join(
            f'{item["title"]} {_pct(item["progress"])}'
            for item in actor.get('psychology', {}).get('ambitions', [])) + '.',
        f'Work today: {actor["schedule"]["work_seconds"]} of '
        f'{actor["schedule"]["work_target_seconds"]} seconds; money {actor["money"]}.',
        'Own thought: ' + actor.get('thought', {}).get('text', '')[:180],
        'Known relationships (my own perspective only): ' + (' '.join(relation_lines) or 'none recorded'),
        'Recent personal journal: ' + (' | '.join(beat['narration'][:180] for beat in reversed(beats)) or 'none'),
        'A surprising choice is fine occasionally, but protect immediate safety, resources, and consent.',
    ]
    criteria = {}
    mapped = {}
    for index, option in enumerate(options):
        key = f'option_{index:02}'
        target = by_id.get(option.get('target_id'), 'the neighborhood')
        activity = option['kind'].replace('_', ' ')
        social = option.get('social_category')
        description = f'{activity}' + (f' / {social.replace("_", " ")}' if social else '')
        criteria[key] = f'{description} with/at {target}. '
        criteria[key] += f'Local priority {option["score"]:.2f}; still subject to runtime revalidation.'
        mapped[key] = {'action': option['kind'], 'target_id': option.get('target_id'),
                       'social_category': social}
    return {'state': '\n'.join(lines), 'criteria': criteria, 'options': mapped,
            'actor_id': actor_id, 'owner_epoch': actor['owner_epoch'],
            'expected_version': actor['version'], 'snapshot_version': packet['snapshot_version'],
            'described_at': world.now}


def parse_decision(data: dict, options: dict) -> dict:
    answer = data.get('answers', {}).get('next_action', {})
    if answer.get('type') != 'choice':
        raise ProviderUnavailable('Decision provider returned no typed choice')
    raw = answer.get('probabilities') or {}
    probabilities = {}
    for key in options:
        value = raw.get(key, 0)
        if not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
            raise ProviderUnavailable('Decision provider returned invalid probabilities')
        probabilities[key] = float(value)
    if sum(probabilities.values()) <= 0:
        selected = answer.get('choice')
        if selected not in options:
            raise ProviderUnavailable('Decision provider chose an unavailable action')
        probabilities[selected] = 1.0
    try:confidence = float(answer.get('confidence', 0))
    except (TypeError, ValueError):confidence = 0
    if not math.isfinite(confidence):confidence = 0
    return {'probabilities': probabilities,
            'confidence': min(1.0, max(0.0, confidence)),
            'model': str(data.get('model', ''))[:100]}


def sample_option(decision: dict, rng) -> str:
    weights = decision['probabilities']
    total = sum(weights.values())
    draw = rng.random() * total
    for key, weight in weights.items():
        if weight <= 0:
            continue
        draw -= weight
        if draw < 0:
            return key
    return next(key for key in reversed(weights) if weights[key] > 0)


def request_decision(model: str, description: dict, *, key: str | None = None,
                     transport=None) -> dict:
    if model not in MODELS:
        raise ProviderUnavailable('Unsupported decision model')
    token = (key or os.environ.get('OPENROUTER_API_KEY', '')).strip()
    if not token:
        raise ProviderUnavailable('OPENROUTER_API_KEY is not configured')
    if not description['criteria']:
        raise ProviderUnavailable('No currently feasible action options')
    payload = {'model': model, 'state': description['state'],
               'questions': {'next_action': {
                   'type': 'choice',
                   'instructions': 'Which currently feasible next action best fits this resident now? '
                                   'Consider personality, needs, commitments, relationships and a small chance of surprise.',
                   'criteria': description['criteria']}}}
    if transport is None:
        def transport(body):
            request = Request(DECISIONS_URL, data=json.dumps(body).encode('utf-8'),
                              headers={'Authorization': 'Bearer ' + token,
                                       'Content-Type': 'application/json',
                                       'HTTP-Referer': 'http://127.0.0.1',
                                       'X-Title': 'Open Sims local prototype'},
                              method='POST')
            with urlopen(request, timeout=12) as response:
                return json.load(response)
    try:
        result = transport(payload)
        return parse_decision(result, description['options'])
    except ProviderUnavailable:
        raise
    except HTTPError as exc:
        if exc.code == 429:
            raise ProviderUnavailable('Rate limit reached; retrying later', code='rate_limited') from None
        if exc.code in (401, 403):
            raise ProviderUnavailable('OpenRouter rejected the session key; check Settings',
                                      code='authentication', retryable=False) from None
        raise ProviderUnavailable(f'Decision service returned HTTP {exc.code}; retrying later',
                                  code='http_error') from None
    except (TimeoutError, URLError):
        raise ProviderUnavailable('Decision service timed out or is unreachable; retrying later',
                                  code='network') from None
    except Exception as exc:
        # Never include the key, request body, or remote error body in logs/Beats.
        raise ProviderUnavailable(f'Decision service unavailable ({type(exc).__name__}); retrying later',
                                  code='provider_error') from None
