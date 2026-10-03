from fastapi.testclient import TestClient

from living_world.engine import World
from living_world import leisure_drama
from living_world import possessions
from living_world.server import create_app
import random


def test_leisure_micro_scenes_are_seeded_and_site_specific():
    scenes = leisure_drama.ACTIVITY_SCENES
    assert len(scenes) >= 20
    for activity, choices in scenes.items():
        assert activity in leisure_drama.LEISURE_ACTIVITIES
        assert len(set(choices)) >= 3
        assert leisure_drama.scene_for(activity, random.Random(9)) == leisure_drama.scene_for(activity, random.Random(9))
    assert 'Swimming' in leisure_drama.scene_for('swim', random.Random(1)) or 'pool' in leisure_drama.scene_for('swim', random.Random(1))


def test_concrete_dishes_vary_without_changing_recipe_steps():
    for recipe in ('pizza', 'pancake'):
        dishes={possessions.dish_variant({'id':f'resident_{index:03}'},recipe,8*3600)
                for index in (1,2,3)}
        assert len(dishes)==3
        assert all(label in possessions.DISH_VARIANTS[recipe] for label in dishes)


def test_named_conversation_bypasses_utility_shortlist_but_not_consent():
    world = World(seed=73, layout='neighborhood-v1')
    try:
        actor = world.actors['resident_001']
        other = world.actors['resident_002']
        assert world.spatial.visible(world.position_at(actor), world.position_at(other), radius=4)
        assert not any(c.get('social_category') == 'argue' and c.get('target_id') == other['id']
                       for c in world.candidates(actor)[0])
        suggestion = world.recommend(actor['id'], {'expected_version': actor['version'],
            'action': 'chat', 'target_id': other['id'], 'social_category': 'argue'})
        assert suggestion['status'] == 'pending'
        world.decide(actor['id'])
        options = world.actors[actor['id']]['last_decision']['candidates']
        assert any(c.get('social_category') == 'argue' and c.get('target_id') == other['id']
                   and c['terms'].get('player_recommendation') == .65 for c in options)
        assert world.actors[actor['id']]['player_recommendation']['status'] in {'followed', 'considered'}
        assert world.invariants() == []
        assert world.store.replay() == world.canonical_state()
    finally:
        world.close()


def test_known_remote_contact_and_specific_destination():
    world = World(seed=73, layout='neighborhood-v1')
    try:
        actor = world.actors['resident_001']
        remote = world.actors['resident_008']
        assert remote['id'] in actor['relations']
        assert not world.spatial.visible(world.position_at(actor), world.position_at(remote), radius=4)
        before_paths=world.spatial.path_queries
        before_beats=world.store.sequence
        options = world.intervention_options(actor['id'])
        assert world.spatial.path_queries==before_paths
        assert world.store.sequence==before_beats
        contact = next(row for row in options['contacts'] if row['id'] == remote['id'])
        assert 'phone_call' in contact['categories']
        assert 'small_talk' not in contact['categories']
        phone = world.recommend(actor['id'], {'expected_version': actor['version'],
            'action': 'chat', 'target_id': remote['id'], 'social_category': 'phone_call'})
        assert phone['target_id'] == remote['id']
        destination = next(row for row in options['places'] if row['object'] == 'Academic bookshelves')
        assert destination['action'] == 'read'
        place = world.recommend(actor['id'], {'expected_version': world.actors[actor['id']]['version'],
            'action': destination['action'], 'target_id': destination['target_id']})
        assert place['target_id'] == destination['target_id']
        world.decide(actor['id'])
        assert any(row['kind'] == 'read' and row.get('target_id') == destination['target_id']
                   and row['terms'].get('player_recommendation') == .65
                   for row in world.actors[actor['id']]['last_decision']['candidates'])
        assert world.invariants() == []
        assert world.store.replay() == world.canonical_state()
    finally:
        world.close()


def test_left_navigation_and_intervention_api_contract():
    with TestClient(create_app(':memory:', seed=73, layout='neighborhood-v1', paused=True)) as client:
        for path in ('/', '/atelier', '/workshop', '/city', '/api/insights',
                     '/api/actors/resident_001/relationships', '/api/actors/resident_001/interventions',
                     '/static/app.js', '/static/insights-ui.js', '/static/intervention-ui.js',
                     '/static/intervention-ui.css'):
            assert client.get(path).status_code == 200, path
        assert client.get('/api/actors/unknown/interventions').status_code == 404
        html = client.get('/').text
        assert 'id="open-interventions"' in html
        assert 'id="insights-dialog"' in html
        assert 'id="relationships-dialog"' in html
        contact = next(row for row in client.get('/api/actors/resident_001/interventions').json()['contacts']
                       if row['id'] == 'resident_002')
        assert 'small_talk' in contact['categories']
        person = client.get('/api/actors/resident_001').json()
        result = client.post('/api/recommendations', json={'actor_id':person['id'],
            'expected_version':person['version'], 'action':'chat', 'target_id':contact['id'],
            'social_category':'small_talk'})
        assert result.status_code == 200, result.text
        # The UI endpoint reads the version under the same world lock as the
        # recommendation, so it does not race a busy simulation tick.
        payload={'actor_id':person['id'],'action':'chat','target_id':contact['id'],
                 'social_category':'small_talk'}
        second=client.post('/api/player/recommendations',json=payload)
        assert second.status_code==200,second.text
        stale=client.post('/api/recommendations',json={**payload,'expected_version':person['version']})
        assert stale.status_code==409
        unknown=client.post('/api/player/recommendations',json={**payload,'target_id':'missing'})
        assert unknown.status_code==409
        assert client.get('/api/health').json()['invariants']==[]
        client.app.state.world.fault='Save failed: disk full'
        blocked=client.post('/api/player/recommendations',json=payload)
        assert blocked.status_code==503
        assert client.get('/api/actors/resident_001/interventions').json()['fault']=='Save failed: disk full'
