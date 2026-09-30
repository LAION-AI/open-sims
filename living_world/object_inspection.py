"""Read-only player observation; never an authorization to use an object."""
from copy import deepcopy
from .daily_life import daily_state


def inspect_object(world, object_id):
    obj=world.objects[object_id]
    building=next((b for b in world.spatial.buildings if b['id']==obj.get('building_id')),None)
    actions=[{'id':key,'label':action['label'],'duration_seconds':action['duration'],
              'relief':deepcopy(action['relief']),'cost':action.get('cost',0)}
             for key,action in world.rules.actions.items() if obj['kind'] in action.get('object_kinds',[])]
    users=[]
    contents=[]
    for actor in world.actors.values():
        action=actor.get('action')
        if action and action.get('target_id')==object_id:
            users.append({'actor_id':actor['id'],'name':actor['name'],'action':action['kind'],
                          'label':action['label'],'phase':action['phase'],'ends_at':action['ends_at']})
        for item in actor.get('belongings',[]):
            if item.get('location')=={'type':'container','id':object_id}:
                contents.append({**deepcopy(item),'custodian_id':actor['id'],
                                 'custodian_name':actor['name']})
    return {'schema':'mosswood.object-inspection/1','clock':world.now,
            'snapshot_version':world.store.sequence,'object':deepcopy(obj),
            'building':{'id':building['id'],'name':building['name']} if building else None,
            'users':users,'contents':contents,'contents_complete':True,'actions':actions,
            'effective_daily':deepcopy(daily_state(obj)),
            'default_daily_keys':[key for key in daily_state(obj) if key not in obj.get('daily',{})],
            'authority':'Player observation only. Actions are type capabilities, not validated actor intentions.'}
