"""Fictional career tracks driven by completed work at physical stations.

Old saves start at zero recorded experience; no past shifts are inferred.
"""
from copy import deepcopy


# Occupations can share a station but have distinct tasks, skills and pay.
CAREERS = {
    'Teacher': ('teaching', 'Prepare a lesson', 1.05, 8),
    'Illustrator': ('craft', 'Finish an illustration', 1.00, 9),
    'Designer': ('craft', 'Review a design', 1.10, 9),
    'Carpenter': ('craft', 'Build a joinery piece', 1.05, 8),
    'Tailor': ('craft', 'Cut and sew garments', .95, 8),
    'Gardener': ('gardening', 'Care for public planting', .95, 7),
    'Baker': ('cooking', 'Bake for the morning counter', 1.00, 6),
    'Bookseller': ('retail', 'Help readers find a book', .95, 9),
    'Nurse': ('care', 'Support the clinic team', 1.15, 7),
    'Firefighter': ('response', 'Check equipment and dispatch', 1.15, 8),
    'Civic clerk': ('administration', 'Process residents’ requests', 1.00, 9),
    'Office analyst': ('analysis', 'Study an office report', 1.10, 9),
    'Fitness coach': ('fitness', 'Guide a training session', 1.00, 10),
    'Retail assistant': ('retail', 'Restock and serve customers', .95, 9),
    'Independent artist': ('craft', 'Develop a home studio project', .90, 10),
    'Physician': ('care', 'Review a clinic case', 1.20, 8),
    'Chef': ('cooking', 'Prepare the café menu', 1.10, 7),
    'Mechanic': ('craft', 'Repair workshop equipment', 1.05, 8),
    'Programmer': ('analysis', 'Build an office tool', 1.10, 9),
    'Civic planner': ('administration', 'Review a neighborhood plan', 1.10, 9),
    'Kindergarten educator': ('teaching', 'Guide early learning', 1.00, 8),
    'Lifeguard': ('response', 'Watch the swimming lanes', 1.00, 9),
    'Bartender': ('service', 'Mix and serve drinks', 1.00, 17),
    'Club DJ': ('music', 'Prepare the evening set', 1.05, 18),
    'Professor': ('teaching', 'Lead a university seminar', 1.25, 9),
    'Researcher': ('analysis', 'Run a careful laboratory study', 1.18, 9),
    'University administrator': ('administration', 'Coordinate campus services', 1.06, 9),
}
LEVEL_THRESHOLDS = (0, 8, 24, 48)


def initial(actor, now=0):
    job = actor.get('profile', {}).get('job', 'Independent artist')
    if job in {'Kindergarten child','Pupil','Retired','Student'}:
        return {'job':job,'skill':None,'task':'Play and learn' if job=='Kindergarten child' else 'Attend school' if job=='Pupil' else 'Attend university' if job=='Student' else 'Enjoy retirement',
                'pay_factor':0,'level':0,'experience_hours':0.0,'completed_shifts':0,
                'performance':.5,'started_at':now,'last_shift':None,
                'schedule_start':9*3600 if job=='Student' else 8*3600+30*60,'evidence_id':'initialization'}
    skill, task, factor, start = CAREERS.get(job, CAREERS['Independent artist'])
    return {'job': job, 'skill': skill, 'task': task, 'pay_factor': factor,
            'level': 1, 'experience_hours': 0.0, 'completed_shifts': 0,
            'performance': .5, 'started_at': now, 'last_shift': None,
            'schedule_start': start * 3600, 'evidence_id': 'initialization'}


def complete_shift(actor, duration_seconds, now, evidence_id, base_income):
    """Return a pure career/skill patch and coin income for one real shift."""
    career = deepcopy(actor.get('career') or initial(actor, now))
    skills = deepcopy(actor.get('skills', {}))
    duration = max(0, int(duration_seconds))
    pressures = actor.get('needs', {})
    readiness = max(.2, 1 - .5 * max(float(pressures.get('fatigue', 0)),
                                      float(pressures.get('hunger', 0))))
    skill = career['skill']
    proficiency = float(skills.get(skill, .15))
    gained = round(duration / 3600 * readiness * (.75 + .25 * proficiency), 4)
    career['experience_hours'] = round(float(career.get('experience_hours', 0)) + gained, 4)
    career['completed_shifts'] = int(career.get('completed_shifts', 0)) + 1
    career['level'] = max(i + 1 for i, threshold in enumerate(LEVEL_THRESHOLDS)
                          if career['experience_hours'] >= threshold)
    career['performance'] = round(.7 * float(career.get('performance', .5)) + .3 * readiness, 4)
    career['last_shift'] = now
    career['evidence_id'] = evidence_id
    skills[skill] = round(min(1, proficiency + duration / 3600 * .003), 4)
    income = max(1, round(base_income * float(career['pay_factor']) + 2 * (career['level'] - 1)))
    return {'career': career, 'skills': skills, 'income': income}
