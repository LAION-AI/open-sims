from living_world.engine import World
from unittest.mock import patch


def test_new_world_has_leisure_sites_and_bounded_bubbles():
    world=World(database=':memory:',layout='neighborhood-v1')
    try:
        kinds={candidate['kind'] for candidate in world.candidates(world.actors['resident_001'])[0]}
        assert any(kind.startswith('leisure_') for kind in kinds)
        assert world.rules.version=='3.3.0'
        world.advance(60)
        speech=[person['speech']['text'] for person in world.snapshot()['actors'] if person['speech']]
        assert speech and all(1<=len(phrase.split())<=5 for phrase in speech)
        assert world.invariants()==[]
    finally:world.close()


def test_work_produces_career_specific_journal_microtasks():
    world=World(database=':memory:',layout='neighborhood-v1')
    try:
        world.advance(7200)
        beats=world.store.recent(limit=3000)
        tasks=[beat for beat in beats if beat['rule_id']=='work.microtask.v1']
        assert tasks
        assert any('completed' in beat['narration'] for beat in tasks)
        assert world.invariants()==[]
    finally:world.close()


def test_firing_and_job_application_are_coordinator_events():
    world=World(database=':memory:',layout='neighborhood-v1')
    try:
        aid='resident_004'
        with world.transaction('test.isolate_employment',list(world.actors),'Employment fixture.'):
            for other_id in world.actors:
                if other_id!=aid:world.edit('actors',other_id)['owner']='external'
        workplace=world.actors[aid]['workplace']
        assert workplace
        world.decide(aid,{'action':'work','target_id':workplace['target_id']})
        ends_at=world.actors[aid]['action']['ends_at']
        with patch('living_world.engine.work_life.evaluate_job_security',return_value={'event':'fired'}):
            world.advance(ends_at-world.now)
        actor=world.actors[aid]
        assert actor['profile']['job']=='Unemployed'
        assert actor['workplace'] is None
        assert actor['schedule']['work_target_seconds']==0
        assert any(c['kind']=='job_search' for c in world.candidates(actor)[0])
        world.decide(aid,{'action':'job_search'})
        ends_at=world.actors[aid]['action']['ends_at']
        with patch('living_world.engine.work_life.evaluate_hire',return_value={
                'event':'hired','job':'Programmer'}):
            world.advance(ends_at-world.now)
        actor=world.actors[aid]
        assert actor['profile']['job']=='Programmer'
        assert actor['workplace']['target_id'] in world.objects
        assert world.invariants()==[]
        assert world.store.replay()==world.canonical_state()
    finally:world.close()
