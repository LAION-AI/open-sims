from fastapi.testclient import TestClient

from living_world.engine import World
from living_world.insights import build_world_insights
from living_world.server import create_app


def test_insights_are_bounded_read_only_and_consistent():
    world = World(database=':memory:', layout='neighborhood-v1')
    try:
        before = world.canonical_state()
        sequence = world.store.sequence
        result = build_world_insights(world)
        assert result['population'] == len(world.actors)
        assert sum(row['count'] for row in result['demographics']) == len(world.actors)
        assert sum(row['count'] for row in result['professions']) == len(world.actors)
        assert sum(row['count'] for row in result['moods']) == len(world.actors)
        assert len(result['events']) <= 50
        assert all(item['id'] in world.actors for item in result['ambitions'])
        assert world.canonical_state() == before
        assert world.store.sequence == sequence
    finally:
        world.close()


def test_insights_api_responds_without_simulation_advance():
    with TestClient(create_app(':memory:', layout='neighborhood-v1', paused=True)) as client:
        html = client.get('/').text
        assert 'id="insights-toggle"' in html
        assert 'id="insights-dialog"' in html
        assert client.get('/static/insights-ui.js').status_code == 200
        assert client.get('/static/insights-ui.css').status_code == 200
        first = client.get('/api/state').json()
        response = client.get('/api/insights')
        assert response.status_code == 200, response.text
        data = response.json()
        assert data['population'] == first['population']
        assert sum(group['count'] for group in data['demographics']) == first['population']
        assert client.get('/api/state').json()['clock'] == first['clock']
