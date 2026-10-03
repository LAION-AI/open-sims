import random
import time
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from living_world.engine import World
from living_world.server import create_app
from living_world import openrouter_control as control


def test_bounded_actor_description_and_typed_choice():
    world = World(database=':memory:', layout='neighborhood-v1')
    try:
        packet = control.describe_actor(world, 'resident_001')
        assert 'Personality:' in packet['state']
        assert 'Recent personal journal:' in packet['state']
        assert 'Known relationships' in packet['state']
        assert 'Current needs' in packet['state']
        assert packet['criteria'] and len(packet['options']) <= 24
        assert all(key.startswith('option_') for key in packet['options'])

        def fake_transport(body):
            assert body['model'] == 'inception/mercury-decide:free'
            assert body['state'] == packet['state']
            assert body['questions']['next_action']['criteria'] == packet['criteria']
            first = next(iter(packet['options']))
            return {'answers': {'next_action': {'type':'choice', 'choice':first,
                    'probabilities':{first:1}, 'confidence':.7}}, 'model':body['model']}

        result = control.request_decision('inception/mercury-decide:free',packet,
                                          key='fake-test-token',transport=fake_transport)
        assert control.sample_option(result,random.Random(2)) in packet['options']
        assert result['confidence'] == .7
        with pytest.raises(control.ProviderUnavailable):
            control.request_decision('unknown/model',packet,key='fake-test-token',transport=fake_transport)
    finally:
        world.close()


def test_http_provider_error_is_classified_without_response_body():
    packet = {'state': 'Local test', 'criteria': {'option_00': 'Wait'},
              'options': {'option_00': {'action': 'wait', 'target_id': None}}}

    def denied(_):
        raise HTTPError('https://openrouter.ai/api/alpha/decisions', 429,
                        'secret response body', {}, None)

    with pytest.raises(control.ProviderUnavailable) as error:
        control.request_decision('typesafe/jev-1.13', packet,
                                 key='fake-test-token', transport=denied)
    assert error.value.retryable
    assert 'secret' not in str(error.value)


def test_provider_api_opt_in_is_per_sim_and_server_only(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','fake-test-token')
    with TestClient(create_app(':memory:',layout='neighborhood-v1',paused=True)) as client:
        status = client.get('/api/decision-providers').json()
        assert status['configured'] is True
        assert 'fake-test-token' not in repr(status)
        actor = client.get('/api/actors/resident_001').json()
        other = client.get('/api/actors/resident_002').json()
        enabled = client.post('/api/actors/resident_001/decision-provider',json={
            'enabled':True,'model':'typesafe/jev-1.13','expected_version':actor['version']})
        assert enabled.status_code == 200, enabled.text
        state = client.get('/api/actors/resident_001').json()
        assert state['owner'] == 'external' and state['decision_provider']['model'] == 'typesafe/jev-1.13'
        assert client.get('/api/actors/resident_002').json()['owner'] == other['owner']
        assert 'fake-test-token' not in repr(client.get('/api/state').json())
        switched = client.post('/api/actors/resident_001/decision-provider', json={
            'enabled': True, 'model': 'inception/mercury-decide:free',
            'expected_version': state['version']})
        assert switched.status_code == 200, switched.text
        state = client.get('/api/actors/resident_001').json()
        assert state['decision_provider']['model'] == 'inception/mercury-decide:free'
        disabled = client.post('/api/actors/resident_001/decision-provider',json={
            'enabled':False,'expected_version':state['version']})
        assert disabled.status_code == 200, disabled.text
        assert client.get('/api/actors/resident_001').json()['owner'] == 'procedural'


def test_unconfigured_provider_is_not_enabled(monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
    with TestClient(create_app(':memory:',paused=True)) as client:
        actor = client.get('/api/actors/resident_001').json()
        result = client.post('/api/actors/resident_001/decision-provider',json={
            'enabled':True,'model':'inception/mercury-decide:free',
            'expected_version':actor['version']})
        assert result.status_code == 503
        assert client.get('/api/actors/resident_001').json()['owner'] == 'procedural'


def test_transient_failure_keeps_opt_in_and_uses_procedural_fallback(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fake-test-token')
    calls = []

    def rate_limited(model, description, *, key):
        calls.append(model)
        raise control.ProviderUnavailable('Decision service rate-limited; retrying later',
                                          code='rate_limit', retryable=True)

    monkeypatch.setattr(control, 'request_decision', rate_limited)
    with TestClient(create_app(':memory:', layout='neighborhood-v1', paused=True)) as client:
        actor = client.get('/api/actors/resident_001').json()
        response = client.post('/api/actors/resident_001/decision-provider', json={
            'enabled': True, 'model': 'typesafe/jev-1.13', 'expected_version': actor['version']})
        assert response.status_code == 200
        client.post('/api/control', json={'paused': False, 'speed': 1})
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            current = client.get('/api/actors/resident_001').json()
            if current.get('decision_provider_error') and current.get('last_decision'):
                break
            time.sleep(.1)
        assert calls
        assert current['decision_provider']['model'] == 'typesafe/jev-1.13'
        assert current['decision_provider']['status'] == 'retrying'
        assert current['owner'] == 'external'
        assert current['last_decision']['policy'].startswith('procedural')
        assert 'fake-test-token' not in repr(current)
        assert client.get('/api/health').json()['status'] == 'ok'


def test_forgetting_session_key_preserves_model_preference(monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    with TestClient(create_app(':memory:', layout='neighborhood-v1', paused=True)) as client:
        assert client.post('/api/settings/openrouter-key', json={'key': 'fake-test-token'}).status_code == 200
        actor = client.get('/api/actors/resident_001').json()
        assert client.post('/api/actors/resident_001/decision-provider', json={
            'enabled': True, 'model': 'inception/mercury-decide:free',
            'expected_version': actor['version']}).status_code == 200
        assert client.delete('/api/settings/openrouter-key').status_code == 200
        current = client.get('/api/actors/resident_001').json()
        assert current['decision_provider']['model'] == 'inception/mercury-decide:free'
        assert current['owner'] == 'external'
        assert client.get('/api/decision-providers').json()['configured'] is False
