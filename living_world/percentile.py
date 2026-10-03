"""Original, deterministic percentile checks for fictional everyday tasks.

This is a small roll-under game mechanic, not an implementation of a licensed
tabletop ruleset. A check grades *how* a completed action went; it never grants
social consent, replaces path finding, or invents an action that did not occur.
"""
from __future__ import annotations

from copy import deepcopy

ATTRIBUTES = ('reasoning', 'coordination', 'presence', 'resolve', 'perception',
              'stamina', 'strength')
SOCIAL_SKILLS = {
    'tell_joke': ('humor', 'presence'),
    'compliment': ('charm', 'presence'),
    'flirt': ('charm', 'presence'),
    'ask_date': ('charm', 'presence'),
    'apologize': ('empathy', 'presence'),
    'reconcile': ('empathy', 'presence'),
    'check_in': ('empathy', 'perception'),
    'offer_help': ('empathy', 'perception'),
    'ask_help': ('persuasion', 'presence'),
    'confide': ('resolve', 'resolve'),
    'set_boundary': ('resolve', 'resolve'),
    'undermine': ('persuasion', 'presence'),
    'gossip': ('persuasion', 'presence'),
    'challenge': ('humor', 'presence'),
    'coordinate_work': ('teamwork', 'reasoning'),
    'share_news': ('persuasion', 'presence'),
    'invite_activity': ('persuasion', 'presence'),
    'share_interest': ('charm', 'presence'),
    'small_talk': ('charm', 'presence'),
    'greet': ('charm', 'presence'),
    'celebrate': ('humor', 'presence'),
    'play_together': ('teamwork', 'presence'),
    'phone_call': ('charm', 'presence'),
    'deep_talk': ('empathy', 'perception'),
    'comfort': ('empathy', 'perception'),
    'ask_favor': ('persuasion', 'presence'),
    'collaborate_project': ('teamwork', 'reasoning'),
    'persuade': ('persuasion', 'reasoning'),
    'make_plans': ('teamwork', 'reasoning'),
    'invite_to_dinner': ('charm', 'presence'),
    'tell_story': ('humor', 'presence'),
    'tease': ('humor', 'presence'),
    'debate': ('persuasion', 'reasoning'),
    'provoke': ('persuasion', 'presence'),
    'argue': ('resolve', 'resolve'),
}
PROFESSION_ATTRIBUTES = {
    'teaching': 'presence', 'craft': 'coordination', 'gardening': 'stamina',
    'cooking': 'perception', 'retail': 'presence', 'care': 'perception',
    'response': 'resolve', 'administration': 'reasoning',
    'analysis': 'reasoning', 'fitness': 'stamina', 'service': 'coordination',
    'music': 'perception',
}


def _bounded(value, low=1, high=99):
    return max(low, min(high, int(round(value))))


def initial(actor, rng):
    """Stable W100 capabilities; existing normalized career skills remain canonical."""
    big = actor.get('psychology', {}).get('big_five', {})
    biases = {
        'reasoning': big.get('openness', .5),
        'coordination': big.get('conscientiousness', .5),
        'presence': big.get('extraversion', .5),
        'resolve': big.get('conscientiousness', .5),
        'perception': big.get('openness', .5),
        'stamina': 1 - big.get('neuroticism', .5),
        'strength': .5,
    }
    attributes = {name: _bounded(31 + 22 * biases[name] + rng.randint(0, 29), 20, 85)
                  for name in ATTRIBUTES}
    social = {name: _bounded(23 + attributes[attribute] * .35 + rng.randint(0, 26), 20, 85)
              for name, attribute in sorted(set(SOCIAL_SKILLS.values()))}
    # One skill may be paired with different attributes. The skill is stored once.
    return {'attributes': attributes, 'social_skills': social, 'last_check': None,
            'version': 1}


def ensure(actor, rng):
    if actor.get('aptitudes', {}).get('version') == 1:
        return deepcopy(actor['aptitudes'])
    return initial(actor, rng)


def difficulty_for(task, *, social=False, target=None, context=None):
    """Explainable integer modifier inferred from task demand and current context.

    Positive numbers make a check harder. Keyword bands are deliberately narrow:
    a complex work task is harder than routine service, but no job is doomed by
    a string match. Callers may supply bounded environmental modifiers.
    """
    context = context or {}
    words = str(task).lower()
    hard = ('rescue', 'diagnos', 'stubborn', 'dispute', 'crisis', 'risky',
            'difficult', 'complex', 'emergency', 'argument', 'repair')
    easy = ('tidy', 'sweep', 'wipe', 'restock', 'greet', 'water', 'sort')
    complexity = 13 if any(word in words for word in hard) else -7 if any(
        word in words for word in easy) else 0
    if social and target:
        relation = target.get('relations', {}).get(context.get('actor_id'), {})
        complexity += round(17 * relation.get('tension', 0)
                            - 10 * relation.get('trust', .4))
    complexity += _bounded(context.get('environment', 0), -20, 20) if context.get('environment') else 0
    return max(-25, min(30, complexity))


def resolve(actor, task, rng, *, skill=None, attribute=None, social=False,
            target=None, context=None):
    """Roll 1..100; return full inputs, threshold and a graded outcome.

    ``rng`` must be an injected, seeded Random-like object. A target only
    modifies difficulty from the target's *known* relation, not hidden thoughts.
    """
    if not hasattr(rng, 'randint'):
        raise TypeError('A seeded randint-capable RNG is required')
    apt = actor.get('aptitudes') or initial(actor, rng)
    if social:
        skill, attribute = SOCIAL_SKILLS.get(task, ('charm', 'presence'))
        skill_rating = apt['social_skills'].get(skill, 45)
    else:
        skill = skill or (actor.get('career') or {}).get('skill') or 'craft'
        attribute = attribute or PROFESSION_ATTRIBUTES.get(skill, 'reasoning')
        skill_rating = _bounded(20 + 75 * actor.get('skills', {}).get(skill, .22), 15, 95)
    attribute_rating = apt['attributes'].get(attribute, 50)
    needs = actor.get('needs', {})
    pressure = round(20 * max(needs.get('fatigue', 0), needs.get('hunger', 0))
                     + 8 * needs.get('thirst', 0))
    modifier = difficulty_for(task, social=social, target=target, context=context)
    threshold = _bounded(.65 * skill_rating + .35 * attribute_rating + 9
                         - pressure - modifier, 5, 95)
    roll = rng.randint(1, 100)
    if roll <= max(1, threshold // 5):
        grade = 'excellent'
    elif roll <= threshold:
        grade = 'success'
    elif roll >= 100 - max(1, (100 - threshold) // 6):
        grade = 'setback'
    else:
        grade = 'mixed'
    return {'task': task, 'skill': skill, 'skill_rating': skill_rating,
            'attribute': attribute, 'attribute_rating': attribute_rating,
            'pressure': pressure, 'difficulty_modifier': modifier,
            'threshold': threshold, 'roll': roll, 'grade': grade,
            'at': context.get('at') if context else None}
