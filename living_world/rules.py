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
        added_jobs = {'Physician', 'Chef', 'Mechanic', 'Programmer', 'Civic planner'}
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
        self.v3_hash = hashlib.sha256(json.dumps(old_v3, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.data['version'] = '3.1.0'
        self.data['coverage']['clothes_storage'] = 'reachable wardrobes in new homes; old saves retain bed fallback'
        self.hash = hashlib.sha256(json.dumps(self.data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.version = self.data["version"]
        self.actions = self.data["actions"]
        self.rates = self.data["need_rates_per_hour"]
        if set(self.actions) != {"eat", "drink", "toilet", "shower", "sleep", "relax", "read", "garden", "work", "chat", "stroll", "wait"} | set(DAILY_ACTIONS) | set(POSSESSION_ACTIONS) | set(SERVICE_ACTIONS):
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
