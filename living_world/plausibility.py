"""Read-only spatial and daily-life audit for a single accepted world state.

Findings point at reusable rules or missing simulation systems. They never
modify an occupied map, infer a child's existence from empty school desks,
or claim that a proposed fix has been tested.
"""
from collections import Counter, deque


def _reachable_in_building(spatial, building):
    bx, by, width, height = (building[k] for k in ('x', 'y', 'w', 'h'))
    residence=building['id']=='student_dorm'
    allowed=[(bx,by,width,height)]
    if residence:
        allowed.extend((b['x'],b['y'],b['w'],b['h']) for b in spatial.buildings
                       if b.get('parent_building')=='student_dorm')
    portals=spatial.planning_metadata.get('portals',[]) if residence else []
    start = tuple(building['door'])
    seen, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        adjacent=[(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
        for portal in portals:
            if tuple(portal['from'])==(x,y):adjacent.append(tuple(portal['to']))
            if tuple(portal['to'])==(x,y):adjacent.append(tuple(portal['from']))
        for point in adjacent:
            px, py = point
            if (any(ax <= px < ax + aw and ay <= py < ay + ah
                    for ax,ay,aw,ah in allowed)
                    and point not in seen and spatial.walkable(point)):
                seen.add(point)
                queue.append(point)
    return seen


def audit(world):
    objects = list(world.objects.values())
    kinds = Counter(obj['kind'] for obj in objects)
    findings = []

    def finding(code, scope, subject, evidence, recommendation, severity='warning'):
        findings.append({'code': code, 'severity': severity, 'scope': scope,
                         'subject_id': subject, 'evidence': evidence,
                         'generator_or_system': recommendation})

    for home in world.spatial.households:
        owned = [o for o in objects if o.get('household_id') == home['id']]
        members = [a for a in world.actors.values() if a['household_id'] == home['id']]
        bedrooms = [o for o in owned if o['kind'] == 'bed']
        tables = [o for o in owned if o['kind'] == 'table']
        wardrobes = [o for o in owned if o['kind'] == 'wardrobe']
        if not wardrobes:
            finding('missing_clothes_storage', 'home', home['building_id'],
                    f'{len(members)} residents; no registered wardrobe',
                    'living home furnishing grammar / clothes-storage program')
        if sum(o['capacity'] for o in bedrooms) < len(members):
            finding('insufficient_sleep_capacity', 'home', home['building_id'],
                    f'{len(members)} residents; {sum(o["capacity"] for o in bedrooms)} bed places',
                    'home occupancy and bedroom generator', 'error')
        dining_capacity=(sum(o['capacity'] for o in tables) if home['id']=='student_residence'
                         else max((o['capacity'] for o in tables),default=0))
        if dining_capacity < len(members):
            finding('insufficient_dining_capacity', 'home', home['building_id'],
                    f'{len(members)} residents; no suitably sized dining table',
                    'dining room generator', 'error')
        building = next(b for b in world.spatial.buildings if b['id'] == home['building_id'])
        reachable = _reachable_in_building(world.spatial, building)
        for wardrobe in wardrobes:
            if not any(tuple(anchor) in reachable for anchor in wardrobe['anchors']):
                finding('unreachable_clothes_storage', 'home', home['building_id'],
                        f'{wardrobe["id"]} has no reachable use anchor',
                        'room clearance and doorway constraints', 'error')

    for actor in world.actors.values():
        workplace = actor.get('workplace')
        if actor['profile']['job'] not in {'Pupil','Kindergarten child','Retired','Unemployed','Student'} and (
                not workplace or workplace.get('target_id') not in world.objects):
            finding('missing_workplace', 'person', actor['id'],
                    f'{actor["profile"]["job"]} has no physical station',
                    'occupation-to-building assignment', 'error')
        minute = world.now % 86400
        schedule = actor.get('schedule', {})
        if (schedule.get('end', 86400) + 900 <= minute < 86400
                and schedule.get('work_seconds', 0) < .25 * schedule.get('work_target_seconds', 0)):
            finding('missed_workday', 'person', actor['id'],
                    f'{schedule.get("work_seconds", 0)} of {schedule.get("work_target_seconds", 0)} scheduled seconds completed',
                    'decision utility, schedule and commute rules')

    pupils = [a for a in world.actors.values() if 6 <= a.get('age', 99) < 18]
    if kinds['school_student_desk'] and not pupils:
        finding('school_population_not_modelled', 'district', 'school',
                f'{kinds["school_student_desk"]} pupil desks; zero eligible pupils',
                'child life phase, enrollment and timetable', 'info')
    return {'schema': 'mosswood.plausibility/1', 'observed_at': world.now,
            'read_only': True, 'population': len(world.actors),
            'households': len(world.spatial.households), 'objects': len(objects),
            'object_kinds': dict(sorted(kinds.items())),
            'occupations': dict(sorted(Counter(a['profile']['job'] for a in world.actors.values()).items())),
            'completed_work_shifts': sum(a.get('career', {}).get('completed_shifts', 0) for a in world.actors.values()),
            'findings': findings}
