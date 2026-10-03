"""Causal storyteller and session credential regressions."""
from copy import deepcopy
from unittest.mock import patch
from fastapi.testclient import TestClient

from living_world import affect, storyteller
from living_world.engine import World
from living_world.psychology import social_candidates
from living_world.server import create_app


class FixedDraw:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


def test_incidents_require_a_completed_named_trigger_and_are_bounded():
    actor = {"age": 35, "money": 10, "needs": {"fun": .5, "comfort": .5, "social": .5},
             "psychology": {"ambitions": [{"kind": "career", "progress": .2}]}}
    assert storyteller.incident_for(actor, {"kind": "wait", "ends_at": 100}, FixedDraw(0)) is None
    event = storyteller.incident_for(actor, {"kind": "work", "ends_at": 100}, FixedDraw(0))
    assert event["id"] == "work_bonus"
    storyteller.apply_incident(actor, event, 100, "beat_1")
    assert actor["money"] == 42
    assert actor["psychology"]["ambitions"][0]["progress"] > .2
    assert storyteller.incident_for(actor, {"kind": "work", "ends_at": 200}, FixedDraw(0)) is None
    assert storyteller.incident_for(actor, {"kind": "work", "ends_at": 86401}, FixedDraw(.9)) is None


def test_gossip_is_hearsay_not_a_direct_relationship():
    speaker = {"id": "a", "name": "Alice", "relations": {"c": {}}, "psychology": {}}
    listener = {"id": "b", "name": "Bob", "relations": {}, "psychology": {}}
    turn = storyteller.social_turn(speaker, listener, "gossip", FixedDraw(0))
    assert turn["subject_id"] == "c"
    storyteller.remember_rumor(listener, "c", "a", 50, "beat_4")
    assert "c" not in listener["relations"]
    assert listener["heard_of"]["c"]["confidence"] == "low"
    graph=affect.social_graph_projection(listener,{"a":speaker,"b":listener,"c":{"id":"c"}},50)
    assert not graph['edges']
    assert graph['heard_of_not_known']==[{'id':'c','source_id':'a','confidence':'low'}]
    assert storyteller.social_turn(speaker, listener, 'challenge', FixedDraw(0))['kind']=='friendly_rivalry'


def test_status_uses_incoming_respect_and_compassion_weights_help():
    lead={"id":"lead","name":"Lead","age":30,"money":30,
          "profile":{"job":"Unemployed","interests":[]},"career":{"level":0},
          "needs":{"social":.4},"relations":{},"psychology":{"social_style":{"compassion":.95}}}
    distressed={"id":"distressed","name":"Neighbor","age":30,"money":30,
                "needs":{"social":.85},"relations":{"lead":{"respect":.95}},
                "profile":{"job":"Unemployed","interests":[]},"psychology":{}}
    admired=storyteller.social_status(lead,{"lead":lead,"distressed":distressed})
    distressed['relations']['lead']['respect']=.15
    assert admired>storyteller.social_status(lead,{"lead":lead,"distressed":distressed})
    helpful=next(x for x in social_candidates(lead,distressed,100) if x['category']=='offer_help')
    lead['psychology']['social_style']['compassion']=.05
    less_helpful=next(x for x in social_candidates(lead,distressed,100) if x['category']=='offer_help')
    assert helpful['score']>less_helpful['score']


def test_adversity_and_affection_adjust_bounded_ruthlessness():
    actor={'psychology':{'social_style':{'ruthlessness':.4,'compassion':.5}}}
    storyteller.adapt_style(actor,'clinic_bill')
    assert actor['psychology']['social_style']['ruthlessness']>.4
    storyteller.adapt_style(actor,'affection')
    assert actor['psychology']['social_style']['ruthlessness']<.4
    assert actor['psychology']['social_style']['compassion']>.5


def test_social_style_seed_and_personal_status_are_exposed():
    world = World(42, ":memory:", layout="neighborhood-v1")
    try:
        person = world.inspect("resident_001")
        style = person["psychology"]["social_style"]
        assert 0 <= style["ruthlessness"] <= 1
        assert 0 <= style["compassion"] <= 1
        assert 0 <= person["social_status"] <= 1
        assert len(person["social_categories"]) >= 24
        assert not world.invariants()
    finally:
        world.close()


def test_incident_commits_only_after_real_trip_and_completion():
    world=World(2718, ':memory:')
    aid='resident_001'
    try:
        with world.transaction('test.isolate_story',[*world.actors], 'Isolate storyteller acceptance test.'):
            for other_id in world.actors:
                actor=world.edit('actors',other_id)
                actor['owner']='procedural' if other_id==aid else 'external'
                actor['action']=None
                actor['routine']=None
                actor['cooldowns']={}
                actor['needs']={kind:.02 for kind in actor['needs']}
                actor['needs_at']=world.now
                actor['schedule'].update(start=0,end=1)
            resident=world.edit('actors',aid)
            resident['needs']['hunger']=.9
            resident['money']=100
            fridge=next(obj for obj in world.objects.values()
                        if obj['household_id']==resident['household_id'] and obj['kind']=='fridge')
            world.edit('objects',fridge['id'])['daily']={'pantry_stock':0}
        event=next(row for row in storyteller.INCIDENTS if row['id']=='grocery_refund')
        world.decide(aid,{'action':'buy_groceries'})
        action=deepcopy(world.actors[aid]['action'])
        before=world.actors[aid]['money']
        assert world.actors[aid].get('last_story_incident') is None
        with patch.object(storyteller,'incident_for',side_effect=lambda actor,step,rng:
                deepcopy(event) if actor['id']==aid and step['kind']=='buy_groceries' else None):
            world.advance(action['ends_at']-world.now)
        actor=world.actors[aid]
        assert actor['last_story_incident']['trigger']=='buy_groceries'
        assert actor['money']==before-world.rules.actions['buy_groceries']['cost']+event['money']
        assert event['text'] in world.store.recent(aid,1)[0]['narration']
        assert not world.invariants()
        assert world.store.replay()==world.canonical_state()
    finally:
        world.close()


def test_runtime_openrouter_key_never_appears_in_responses_or_state():
    with TestClient(create_app(database=":memory:", paused=True)) as client:
        secret = "synthetic-test-only-never-a-real-credential"
        result = client.post("/api/settings/openrouter-key", json={"key": secret})
        assert result.status_code == 200
        assert result.json() == {"configured": True, "source": "runtime"}
        assert result.headers["cache-control"] == "no-store"
        for path in ("/api/settings/openrouter-key", "/api/decision-providers", "/api/health", "/api/state"):
            response = client.get(path)
            assert secret not in response.text
        denied = client.post("/api/settings/openrouter-key", headers={"Origin": "https://elsewhere.example"}, json={"key": secret})
        assert denied.status_code == 403
        assert secret not in denied.text
        oversized='synthetic-oversized-'+('x'*520)
        invalid=client.post('/api/settings/openrouter-key',json={'key':oversized})
        assert invalid.status_code==422
        assert oversized not in invalid.text
        actor=client.get('/api/actors/resident_001').json()
        enabled=client.post('/api/actors/resident_001/decision-provider',json={
            'enabled':True,'model':'inception/mercury-decide:free','expected_version':actor['version']})
        assert enabled.status_code==200
        cleared = client.delete("/api/settings/openrouter-key")
        assert cleared.status_code == 200
        assert secret not in cleared.text
        after=client.get('/api/actors/resident_001').json()
        if not cleared.json()['configured']:
            assert after['owner']=='external'
            assert after['decision_provider']['model']=='inception/mercury-decide:free'
