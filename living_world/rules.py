"""A bounded, declarative action registry. No evaluation of arbitrary rule code."""
import hashlib
import json
from pathlib import Path


class RuleRegistry:
    def __init__(self, path=None):
        raw = Path(path or Path(__file__).with_name("rules.json")).read_bytes()
        self.data = json.loads(raw)
        self.legacy_hash = hashlib.sha256(raw).hexdigest()
        # Keep the shipped 1.0 source intact: its exact hash is the only older
        # package accepted by the explicit, journaled life-system migration.
        from .daily_life import DAILY_ACTIONS, JOB_STATIONS
        from copy import deepcopy
        self.data["actions"].update(deepcopy(DAILY_ACTIONS))
        self.data["actions"]["work"]["object_kinds"] = sorted({kind for kind, _ in JOB_STATIONS.values()})
        self.data["version"] = "2.0.0"
        self.data["selection"]["candidate_limit"] = 40
        self.data["coverage"].update({
            "personality": "five bounded gameplay traits; not a psychological diagnosis",
            "relationships": "explicit kinship/status plus directional quality dimensions",
            "theory_of_mind": "bounded first-order estimates from witnessed interactions",
            "ambitions": "event-driven progress and utility preferences",
            "fears": "observed triggers, cooldowns and temporary appraisal",
            "household_routines": "reserved multi-step meal and cleanup plans",
            "work": "assigned physical workplace and commute; simplified paid tasks",
        })
        # The v2 hash predates the five new career assignments.  Keep its
        # original work-station set for save recognition, while the active
        # package may use the expanded list.
        old_v2 = deepcopy(self.data)
        added_jobs = {'Physician', 'Chef', 'Mechanic', 'Programmer', 'Civic planner',
                      'Kindergarten educator','Lifeguard','Bartender','Club DJ',
                      'Professor','Researcher','University administrator'}
        old_v2['actions']['work']['object_kinds'] = sorted(
            {kind for job, (kind, _) in JOB_STATIONS.items() if job not in added_jobs})
        self.v2_hash = hashlib.sha256(json.dumps(old_v2, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        from .possessions import POSSESSION_ACTIONS
        from .urban_life import SERVICE_ACTIONS, SERVICE_JOBS
        self.data['actions'].update(POSSESSION_ACTIONS)
        self.data['actions'].update(SERVICE_ACTIONS)
        self.data['actions']['buy_groceries']['object_kinds'].append('supermarket_checkout')
        self.data['actions']['work']['object_kinds']=sorted(set(self.data['actions']['work']['object_kinds']) | {kind for kind,_ in SERVICE_JOBS.values()})
        self.data['version']='3.0.0'
        self.data['selection']['candidate_limit']=64
        self.data['coverage'].update(emotions='simultaneous evidenced appraisals; separate self narrative; EmoNet-Face vocabulary',
            possessions='unique owned portable food and wearable items with location/state',
            city='hierarchical laboratory plus appended live service destinations; no traffic or geodata reconstruction')
        # Preserve the exact 3.0 contract hash so occupied saves can opt into
        # the 3.1 action target without a geometry rewrite or invented history.
        from copy import deepcopy as _copy
        old_v3 = _copy(self.data)
        old_v3['actions']['change_outfit']['object_kinds'] = ['bed']
        added_service_actions={'school_day','kindergarten_day','visit_pool','visit_bar','community_meet','visit_patient'}
        campus_work_kinds={JOB_STATIONS[job][0] for job in
                           ('Professor','Researcher','University administrator')}
        added_work_kinds={JOB_STATIONS[job][0] for job in
                          ('Kindergarten educator','Lifeguard','Bartender','Club DJ')} | campus_work_kinds
        for kind in added_service_actions:old_v3['actions'].pop(kind,None)
        old_v3['actions']['work']['object_kinds']=sorted(set(old_v3['actions']['work']['object_kinds'])-added_work_kinds)
        self.v3_hash = hashlib.sha256(json.dumps(old_v3, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.data['version'] = '3.1.0'
        self.data['coverage']['clothes_storage'] = 'reachable wardrobes in new homes; old saves retain bed fallback'
        old_v31=_copy(self.data)
        for kind in added_service_actions:old_v31['actions'].pop(kind,None)
        old_v31['actions']['work']['object_kinds']=sorted(set(old_v31['actions']['work']['object_kinds'])-added_work_kinds)
        self.v31_hash = hashlib.sha256(json.dumps(old_v31, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        from .leisure_drama import activity_definitions
        leisure_sites = {
            'host_party':['sofa'], 'attend_party':['nightclub_floor'], 'ask_on_date':['cafe_counter'],
            'go_on_date':['cafe_counter'], 'dance':['nightclub_floor'], 'karaoke':['nightclub_floor'],
            'board_games':['table'], 'video_games':['desk'], 'read_for_fun':['bookshelf'],
            'write_story':['desk'], 'paint':['desk'], 'play_instrument':['desk'],
            'craft_project':['desk'], 'garden':['planter'], 'cook_for_fun':['counter'],
            'bake_treats':['counter'], 'go_for_walk':['park_marker'], 'hike':['park_marker'],
            'jog':['park_marker'], 'work_out':['gym_station'], 'play_team_sport':['park_marker'],
            'swim':['pool_water'], 'visit_museum':['bookshelf'], 'see_live_music':['nightclub_floor'],
            'watch_movie':['sofa'], 'volunteer':['townhall_desk'], 'shop_for_fun':['mall_counter'],
            'relax_at_home':['sofa'], 'meditate':['sofa','bench'], 'make_friends':['cafe_counter'],
        }
        for name, activity in activity_definitions().items():
            self.data['actions']['leisure_'+name] = {
                'label': activity['label'], 'object_kinds': leisure_sites[name],
                'duration': min(activity['duration_minutes'], 90)*60,
                'relief': {'fun':.38, 'comfort':.08, **({'social':.1} if 'social' in activity['tags'] else {})},
                'cost': 0, 'preference': 'socializing' if 'social' in activity['tags'] else 'relaxing',
                'thought': 'I could make a little time for '+activity['label'].lower()+'.',
                'leisure_activity': name,
            }
        self.data['actions']['job_search'] = {'label':'Looking for a job',
            'object_kinds':['desk','townhall_desk','office_station'], 'duration':1200,
            'relief':{'comfort':.04},'cost':0,'preference':None,
            'thought':'I might find a role that fits me.'}
        self.data['version'] = '3.2.0'
        self.data['coverage'].update(work='profession-specific microtasks, coworker encounters, rare mishaps and employment changes',
            leisure='30 personality-weighted activities with limited site affordances and rare event proposals',
            speech='seeded short colloquial phrases in local SQLite; not verbatim dialogue',
            external_decisions='opt-in bounded action choice through OpenRouter Decisions API when configured')
        old_v32=_copy(self.data)
        old_v32['actions']['work']['object_kinds']=sorted(
            set(old_v32['actions']['work']['object_kinds'])-campus_work_kinds)
        self.v32_hash = hashlib.sha256(json.dumps(old_v32, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        from .campus_life import CAMPUS_ACTIONS
        self.data['actions'].update(CAMPUS_ACTIONS)
        self.data['version']='3.3.0'
        self.data['coverage'].update(
            campus='traversable university, shared residence and portal-linked upper floors',
            percentile='original W100 checks with logged roll, threshold, grade and context')
        self.hash = hashlib.sha256(json.dumps(self.data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.version = self.data["version"]
        self.actions = self.data["actions"]
        self.rates = self.data["need_rates_per_hour"]
        if set(self.actions) != {"eat", "drink", "toilet", "shower", "sleep", "relax", "read", "garden", "work", "chat", "stroll", "wait", "job_search"} | {'leisure_'+name for name in activity_definitions()} | set(DAILY_ACTIONS) | set(POSSESSION_ACTIONS) | set(SERVICE_ACTIONS) | set(CAMPUS_ACTIONS):
            raise ValueError("Rule package uses an unsupported action contract")
        for definition in self.actions.values():
            if not 0 < definition["duration"] <= 86400:
                raise ValueError("Action duration outside supported bounds")
            if not set(definition["relief"]).issubset(self.rates):
                raise ValueError("Unknown need in relief definition")
        if any(not 0 <= rate <= 1 for rate in self.rates.values()):
            raise ValueError("Need rate outside supported bounds")

    def manifest(self):
        return {"id": self.data["id"], "version": self.version, "sha256": self.hash,
                "schema_version": 1, "units": self.data["units"], "coverage": self.data["coverage"]}
