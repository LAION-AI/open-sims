"""Bounded campus affordances and eligibility for the active neighborhood."""

def _action(label, kinds, duration, relief, preference='reading', cost=0):
    return {'label':label,'object_kinds':kinds,'duration':duration,'relief':relief,
            'preference':preference,'cost':cost,'income':0,
            'thought':'I could '+label.lower()+'.'}


CAMPUS_ACTIONS={
    'attend_lecture':_action('Attending a university lecture',['lecture_seat'],3600,
                             {'fun':.05,'social':.04}),
    'attend_seminar':_action('Discussing ideas in a seminar',['seminar_table'],1800,
                             {'fun':.14,'social':.11}),
    'run_lab':_action('Doing a supervised lab exercise',['biology_bench','physics_bench'],2700,
                      {'fun':.18},'craft'),
    'study_library':_action('Studying in the university library',['library_desk'],1500,
                             {'fun':.08,'comfort':.06}),
    'campus_lunch':_action('Eating at the campus cafeteria',['cafeteria_table'],900,
                            {'hunger':.45,'social':.08},'cooking',5),
    'dorm_party':_action('Joining a residence party',['party_speaker'],1800,
                          {'fun':.49,'social':.35},'socializing'),
    'dorm_laundry':_action('Doing laundry at the residence',['laundry_machine'],1200,
                            {'hygiene':.10,'comfort':.13},'relaxing'),
}


def campus_available(actor, kind, now):
    age=actor.get('age',30)
    hour=now%86400//3600
    if kind in {'attend_lecture','attend_seminar','run_lab'}:
        return 18<=age<65 and 8<=hour<17 and (
            actor.get('education',{}).get('university_student') or
            actor.get('profile',{}).get('job') in {'Professor','Researcher'})
    if kind=='study_library':return age>=16 and 8<=hour<22
    if kind=='campus_lunch':return age>=16 and 10<=hour<17
    if kind=='dorm_party':return age>=18 and (hour>=18 or hour<2)
    if kind=='dorm_laundry':return age>=18 and 7<=hour<23
    return False
