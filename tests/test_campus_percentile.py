"""Campus graph, room affordances and original W100 checks."""
import random

from living_world.campus import extend_campus
from living_world.engine import World
from living_world.neighborhood import LivingNeighborhood
from living_world.percentile import difficulty_for, initial, resolve
from living_world.storyteller import group_dynamic


def test_campus_floors_have_only_portal_routes_and_reachable_rooms():
    site=LivingNeighborhood(17)
    assert extend_campus(site,17) is False
    assert site.height==326
    assert [p['kind'] for p in site.planning_metadata['portals']]==['stairs','stairs']
    assert sum(o['kind']=='lecture_seat' for o in site.objects.values())==20
    assert sum(o['kind']=='bed' and o.get('floor',0)>0 for o in site.objects.values())==10
    start=next(b['door'] for b in site.buildings if b['id']=='student_dorm')
    final=next(o['anchors'][0] for o in site.objects.values()
               if o['building_id']=='student_dorm_floor_2' and o['kind']=='bed')
    path=site.path(start,final)
    assert path and any(abs(b[0]-a[0])+abs(b[1]-a[1])>1 for a,b in zip(path,path[1:]))
    assert all(site.walkable(tuple(step)) for step in path)
    for obj in site.objects.values():
        assert obj['capacity']<=len(obj['anchors'])


def test_w100_check_is_reproducible_and_context_sensitive():
    actor={'psychology':{'big_five':{'openness':.75,'conscientiousness':.7,
            'extraversion':.6,'agreeableness':.5,'neuroticism':.2}},
           'career':{'skill':'craft'},'skills':{'craft':.65},
           'needs':{'fatigue':.1,'hunger':.1,'thirst':.1}}
    actor['aptitudes']=initial(actor,random.Random(7))
    first=resolve(actor,'Measure a cabinet panel',random.Random(81))
    assert first==resolve(actor,'Measure a cabinet panel',random.Random(81))
    tired={**actor,'needs':{'fatigue':.9,'hunger':.8,'thirst':.6}}
    assert resolve(tired,'Measure a cabinet panel',random.Random(81))['threshold']<first['threshold']
    assert difficulty_for('Rescue a difficult instrument')>difficulty_for('Wipe a desk')
    assert 5<=first['threshold']<=95 and 1<=first['roll']<=100
    assert first['skill']=='craft' and first['attribute']=='coordination'


def test_live_world_exposes_campus_and_abilities():
    world=World(seed=73,layout='neighborhood-v1')
    try:
        assert world.rules.version=='3.3.0'
        assert world.spatial.planning_metadata['campus_version']==1
        assert all(actor['aptitudes']['version']==1 for actor in world.actors.values())
        student=next((actor for actor in world.actors.values() if actor['education']['university_student']),None)
        assert student is not None
        options={row['kind'] for row in world.candidates(student)[0]}
        assert 'attend_lecture' in options
        assert world.invariants()==[]
    finally:
        world.close()


def test_student_day_reaches_university_and_records_study():
    world=World(seed=73,layout='neighborhood-v1')
    try:
        residents=[a for a in world.actors.values() if a['profile']['job']=='Student']
        assert len(residents)==10
        assert all(a['household_id']=='student_residence' for a in residents)
        world.advance(3*3600)
        assert any(a['schedule']['work_seconds']>0 for a in residents)
        assert any(a['education']['progress_hours']>0 for a in residents)
        assert any(a['aptitudes']['last_check']['task'] in
                   {'attend_lecture','attend_seminar','run_lab','study_library'}
                   for a in residents if a['aptitudes'].get('last_check'))
        assert world.invariants()==[]
        assert world.store.replay()==world.canonical_state()
    finally:
        world.close()


def test_triad_turn_needs_two_joined_companions_and_is_seeded():
    host={'id':'host','name':'Host','psychology':{'social_style':{'compassion':.8}}}
    peers=[{'id':key,'name':key,'relations':{},'psychology':{'social_style':{'competitiveness':.9}}}
           for key in ('one','two')]
    assert group_dynamic(host,peers[:1],random.Random(9)) is None
    first=group_dynamic(host,peers,random.Random(9))
    assert first==group_dynamic(host,peers,random.Random(9))
    if first:
        assert {first['first_id'],first['second_id']}=={'one','two'}
        assert first['outcome'] in {'positive','neutral','negative'}
