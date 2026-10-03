from living_world.engine import World
from living_world.work_life import PROFESSION_TASKS
from living_world.careers import CAREERS


def test_new_neighborhood_has_four_life_stages_and_connected_public_places():
    world=World(database=':memory:',layout='neighborhood-v1')
    try:
        ages=[actor['age'] for actor in world.actors.values()]
        assert any(age<13 for age in ages)
        assert any(13<=age<18 for age in ages)
        assert any(18<=age<66 for age in ages)
        assert any(age>=66 for age in ages)
        assert all(actor['appearance']['age']==actor['age'] for actor in world.actors.values())
        buildings={building['service_kind'] for building in world.spatial.buildings if building.get('service_kind')}
        assert {'school','kindergarten','pool','nightclub','bar','gym','hospital','community_center'}<=buildings
        assert world.spatial.planning_metadata['validated_entrances']==len(world.spatial.buildings)
        assert {'Kindergarten educator','Lifeguard','Bartender','Club DJ'}<=CAREERS.keys()
        assert set(CAREERS)<=PROFESSION_TASKS.keys()
        child=next(a for a in world.actors.values() if a['age']<7)
        child_kinds={row['kind'] for row in world.candidates(child)[0]}
        assert 'kindergarten_day' in child_kinds
        assert 'visit_bar' not in child_kinds and 'work' not in child_kinds
        assert world.invariants()==[]
    finally:world.close()


def test_pupils_commute_and_attend_by_midday():
    world=World(database=':memory:',layout='neighborhood-v1')
    try:
        world.advance(4*3600)
        pupils=[a for a in world.actors.values() if a['age']<18]
        assert pupils and all(a['schedule']['work_seconds']>=3600 for a in pupils)
        assert any(a['profile']['job']=='Kindergarten child' for a in pupils)
        assert world.invariants()==[]
    finally:world.close()
