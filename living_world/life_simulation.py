"""Coordinator-owned integration of psychology and multi-step everyday plans.

Helpers are pure; this mixin applies their patches only in World transactions.
The live renderer and inspect endpoints never cause observations or decisions.
"""
from copy import deepcopy

from . import psychology, storyteller
from . import possessions
from . import careers
from .daily_life import (DAILY_ACTIONS, StepUnavailable, apply_step, assigned_workplace,
                         daily_state, plan_meal, plan_cleaning, plan_hobby)


class LifeSystems:
    def _life_components(self, new_world):
        if new_world:
            for aid, patch in psychology.initial_family_profiles(self.actors,
                    include_minors=getattr(self,'layout','legacy')=='neighborhood-v1').items():
                self.actors[aid].update(patch)
        for aid, actor in self.actors.items():
            actor.update(psychology.migrate_existing_actor(actor, self.rng(aid, 0, "psychology"), self.now))
            if new_world and actor['household_id']=='student_residence':
                actor['age']=18+self.rng(aid,0,'student_age').randrange(7)
                actor['profile']['job']='Student'
                actor['goals'][1]['title']='Attend university'
                actor['schedule'].update(start=9*3600,end=15*3600,
                    work_target_seconds=3*3600,work_seconds=0)
            actor['appearance']['age']=actor['age']
            if new_world and actor['age']<18:
                actor['profile']['job']='Kindergarten child' if actor['age']<7 else 'Pupil'
                actor['goals'][1]['title']='Play and learn' if actor['age']<7 else 'Attend school'
                actor['schedule'].update(start=8*3600+30*60,end=15*3600,
                    work_target_seconds=3*3600,work_seconds=0)
            if new_world and actor['age']>=66:
                actor['profile']['job']='Retired'
                actor['goals'][1]['title']='Enjoy the day'
                actor['schedule']['work_target_seconds']=0
            if new_world and self.layout=='neighborhood-v1' and aid=='resident_027':
                # Staff the new bar even though its original round-robin slot
                # fell on a child. This is a new-save fixture, never a migration.
                actor['profile']['job']='Bartender'
            actor.setdefault("routine", None)
            actor.setdefault("family", {"parent_ids": [], "partner_id": None, "relationship_status": "unspecified"})
            actor.setdefault('career', careers.initial(actor, self.now))
            if new_world and 18<=actor['age']<66 and actor['profile']['job']!='Student':
                actor['schedule']['start'] = actor['career']['schedule_start']
                actor['schedule']['end'] = actor['schedule']['start'] + 8 * 3600
            actor["workplace"] = assigned_workplace(actor, self.objects)
            actor["workplace_id"] = actor["workplace"]["workplace_id"] if actor["workplace"] else None
        for aid, patch in psychology.initialize_social_graph(self.actors, self.now).items():
            self.actors[aid].update(patch)
        self.meta["life_systems"] = {"version": 0, "schema": "everyday-life/2.0",
            "family_initialization": "authored adult-family fixture" if new_world else "legacy biographies preserved; unknown kinship not invented",
            "migration_at": self.now, "personality_is_gameplay_abstraction": True}
        self.meta["animals"] = {"version": 0, "dogs": [{"id": "dog_clover", "name": "Pippin",
            "position": [56, 61], "patrol": [[56, 61], [57, 61], [58, 61], [59, 61], [58, 61], [57, 61]],
            "patrol_index": 0, "behavior": "slow park patrol; no complete pet physiology"}]}
        if getattr(self.spatial,'park_patrol',None):
            dog=self.meta['animals']['dogs'][0]
            dog['patrol']=deepcopy(self.spatial.park_patrol)
            dog['position']=list(dog['patrol'][0])

    def _migrate_life(self, saved):
        """Upgrade only the recognized 1.0 package, recording every addition.

        Existing positions, actions, queue, needs, money, ages and old relationship
        scores stay intact. New geometry is appended south of the old map.
        """
        before_actors = deepcopy(self.actors)
        previous_meta = deepcopy(saved["meta"])
        self._life_components(new_world=False)
        patches = self.actors
        self.actors = before_actors
        additions = []
        for collection, records, previous in (("objects", self.objects, saved["objects"]),
                                                ("world", self.meta, previous_meta)):
            for rid, record in records.items():
                if rid not in previous:
                    additions.append({"collection": collection, "subject_id": rid,
                        "component_path": "$", "new_value": deepcopy(record), "operation": "set",
                        "expected_prior_version": None, "scope": "canonical", "effective_time": self.now,
                        "microstep": len(additions), "evidence_ids": ["migration.life.v2"]})
        self.store.append(self._beat("migration.life.resources.v2", [],
            "Added southern workplaces, household bins and an explicitly authored park dog; existing map cells unchanged.", additions))
        with self.transaction("migration.life.actors.v2", list(self.actors),
                "Added procedural personality, plans and workplace assignments; preserved existing biographies and active actions.",
                ["recognized v1 package", "no inferred marriages or family history"]):
            for aid, patch in patches.items():
                actor = self.edit("actors", aid)
                for key in ("psychology", "family", "routine", "workplace", "workplace_id", "relations", "career"):
                    actor[key] = patch[key]
        self.schedule(self.now + 60, "animal_tick", None, 0)
        # World finishes the story upgrade before writing the new rule checkpoint.

    @staticmethod
    def _apply_actor_patch(actor, patch):
        for key, value in patch.items():
            if key == "relations":
                actor["relations"].update(value)
            else:
                actor[key] = value

    def _life_bias(self, actor, kind):
        return round(psychology.action_bias(actor, kind, now=self.now) * .22, 4)

    def _routine_candidates(self, actor, needs, pos):
        """Offer only the next step, reserving an object when it actually starts."""
        routine = actor.get("routine")
        plans = []
        if routine and routine["index"] < len(routine["steps"]):
            plans.append((routine["kind"], routine["steps"], routine["index"], False))
        else:
            if needs["hunger"] >= .28:
                legacy_food=any(actor['inventory'].get(k,0) for k in ('ingredients','prepared_meal'))
                steps=plan_meal(actor,self.objects) if legacy_food else possessions.plan(actor,self.objects,self.now)
                plans.append(("meal", steps, 0, True))
            plans.append(("cleaning", plan_cleaning(actor, self.objects), 0, True))
            plans.append(("hobby", plan_hobby(actor, self.objects), 0, True))
            if actor.get('outfit_last_day') != self.now//86400:
                plans.append(('outfit',possessions.plan_outfit(actor,self.objects,self.now),0,True))
        results = []
        for plan_kind, steps, index, is_new in plans:
            if not steps or index >= len(steps):
                continue
            step = steps[index]
            kind, obj = step["kind"], self.objects.get(step["target_id"])
            if not obj or obj["condition"] <= .1 or actor["cooldowns"].get(kind, 0) > self.now:
                continue
            definition = self.rules.actions[kind]
            if actor["money"] < definition["cost"]:
                continue
            if not self._step_available(actor,obj,kind):continue
            reserved = {tuple(r["anchor"]) for r in obj["reservations"].values()}
            anchors = [a for a in obj["anchors"] if tuple(a) not in reserved]
            if len(obj["reservations"]) >= obj["capacity"] or not anchors:
                continue
            anchor = min(anchors, key=lambda a: (abs(a[0]-pos[0])+abs(a[1]-pos[1]), a))
            distance = abs(anchor[0]-pos[0])+abs(anchor[1]-pos[1])
            continuing = .22 if not is_new else 0
            goal = needs["hunger"]**2*1.8 + .12 if plan_kind == "meal" else (
                .12 + actor.get("psychology", {}).get("big_five", {}).get("conscientiousness", .5)*.3
                if plan_kind == "cleaning" else needs["fun"]**2*1.35)
            if plan_kind=='outfit':goal=.5
            if plan_kind == "meal" and index <= next((i for i,s in enumerate(steps) if s["kind"] in {"eat_meal","eat_recipe"}), -1) and needs["hunger"] >= .88:
                goal += 2
            score = goal + continuing + self._life_bias(actor, kind) - distance*.0015
            results.append({"kind": kind, "target_id": obj["id"], "anchor": anchor,
                "distance": distance, "score": round(score,5), "routine_kind": plan_kind,
                "routine_steps": steps, "routine_index": index, "new_routine": is_new,
                "terms": {"plan_goal": round(goal,4), "continuity": continuing,
                          "personality": self._life_bias(actor,kind), "travel_cost": round(distance*.0015,4)}})
        return results

    def _repair_routine(self, aid):
        """Replan stale preconditions; never manufacture or discard held tokens."""
        actor = self.actors[aid]
        routine = actor.get("routine")
        if not routine or routine["index"] >= len(routine["steps"]):
            return
        step = routine["steps"][routine["index"]]
        if step["kind"] not in (set(DAILY_ACTIONS)|set(possessions.POSSESSION_ACTIONS)):
            return
        obj = self.objects[step["target_id"]]
        if self._step_available(actor,obj,step['kind']):return
        # Occupied oven/table is transient; abandoning a valid meal would strand food.
        if step['kind'] in {'load_pizza_oven','serve_recipe','bake_pizza'}:return
        with self.transaction("routine.replan.v2", [aid],
                f"{actor['name']} reconsidered a household step because its preconditions changed.",
                [step["kind"], "held inventory retained"]):
            actor = self.edit("actors", aid)
            # Completed chores can have been done by another household member.
            if step["kind"] in {"clear_dishes", "wash_dishes", "empty_trash", "wipe_counter", "bin_trash"}:
                actor["routine"]["index"] += 1
                if actor["routine"]["index"] >= len(actor["routine"]["steps"]):
                    actor["routine"]["status"] = "completed"
            else:
                actor["routine"] = None

    def _start_routine(self, actor, chosen):
        if "routine_steps" not in chosen:
            return
        if chosen["new_routine"]:
            actor["routine"] = {"id": f"plan_{actor['id']}_{actor['decision_id']}",
                "kind": chosen["routine_kind"], "steps": deepcopy(chosen["routine_steps"]),
                "index": chosen["routine_index"], "started_at": self.now, "status": "active"}
        actor["action"]["routine_id"] = actor["routine"]["id"]
        actor["action"]["routine_index"] = chosen["routine_index"]

    def _daily_complete(self, actor, action):
        if action["kind"] in DAILY_ACTIONS:
            obj = self.edit("objects", action["target_id"])
            patch = apply_step(actor, obj, action["kind"])
            actor["inventory"], actor["skills"] = patch["inventory"], patch["skills"]
            obj["daily"] = patch["object_daily"]
        self._apply_possession(actor,action)
        routine = actor.get("routine")
        if routine and action.get("routine_id") == routine["id"]:
            routine["index"] += 1
            routine["status"] = "completed" if routine["index"] >= len(routine["steps"]) else "active"
        activity = "work" if action["kind"] == "work" else self.rules.actions[action["kind"]].get("preference") or action["kind"]
        self._apply_actor_patch(actor, psychology.complete_activity(actor, activity, self.now,
            f"beat_{self.store.sequence+1:08}", duration_seconds=action["duration"]))

    def _social_complete(self, actor, partner, category, outcome):
        evidence = f"beat_{self.store.sequence+1:08}"
        for aid, patch in psychology.apply_social(actor, partner, category, outcome, self.now, evidence).items():
            self._apply_actor_patch(self.edit("actors", aid), patch)
        for person, other in ((actor,partner), (partner,actor)):
            cue = f"social:{category}:{outcome}"
            self._apply_actor_patch(person, psychology.observe(person, other["id"], cue, self.now, evidence, "participation"))
            tone=psychology.SOCIAL_CATEGORIES[category]["tone"]
            feeling=("Disappointed" if person is actor else "Reserved") if outcome=="declined" else (
                "Tense" if tone in {"conflict","tension"} else "Disappointed") if outcome=="negative" else (
                "Affectionate" if tone=="romance" else "Tense" if tone in {"conflict","tension"} else
                "Relieved" if tone=="repair" else "Playful" if tone=="play" else "Connected")
            person["psychology"]["social_appraisal"]={"type":feeling,"category":category,
                "outcome":outcome,"evidence_id":evidence,"subject_id":other['id'],"expires_at":self.now+900,
                "adult_relation":person.get('age',0)>=18 and other.get('age',0)>=18 and tone=='romance'}
            if outcome in {'positive','accepted'} and category in {'express_affection','check_in','offer_help'}:
                storyteller.adapt_style(person,'affection')

    def _check_fears(self, aid):
        actor = self.actors[aid]
        if "psychology" not in actor:
            return
        fears = {f["kind"]: f for f in actor["psychology"].get("fears", [])}
        event, source = None, None
        if fears.get("dogs", {}).get("intensity", 0) >= .25 and actor["cooldowns"].get("fear:dogs",0) <= self.now:
            for dog in self.meta.get("animals", {}).get("dogs", []):
                if self.spatial.visible(self.position_at(actor), dog["position"], radius=5):
                    event, source = "dog_encounter", dog["id"]
                    break
        minute = self.now % 86400
        if event is None and minute > actor["schedule"]["end"] and actor["schedule"]["work_seconds"] < actor["schedule"]["work_target_seconds"]*.5 and actor["cooldowns"].get("fear:job_loss",0) <= self.now:
            event, source = "work_failed_deadline", actor["workplace"]["workplace_id"] if actor.get("workplace") else None
        if event:
            with self.transaction("psychology.fear.v2", [aid],
                    f"{actor['name']} felt uneasy: {'a dog was visible nearby' if event=='dog_encounter' else 'today’s work target was missed; job loss is a worry, not a fact'}.",
                    ["direct visibility" if event == "dog_encounter" else "own recorded work progress"]):
                actor = self.edit("actors", aid)
                evidence = f"beat_{self.store.sequence+1:08}"
                self._apply_actor_patch(actor, psychology.update_fears(actor, event, self.now, evidence))
                actor["cooldowns"]["fear:dogs" if event == "dog_encounter" else "fear:job_loss"] = self.now + (3600 if event == "dog_encounter" else 86400)
                actor["psychology"]["active_fear"] = {"kind": "dogs" if event == "dog_encounter" else "job_loss",
                    "source": source, "event": event, "evidence_id": evidence, "since": self.now, "expires_at": self.now+1200}
                self._perceive(actor, "I saw a dog nearby." if event == "dog_encounter" else "I missed my own work target today.", source or aid, "sight" if event == "dog_encounter" else "self_observation")
                self._appraise(actor, event)

    def _animal_tick(self):
        with self.transaction("animal.patrol.v1", [], "Pippin moves along the park path.", ["authored, walkable patrol"]):
            animal_state = self.edit("world", "animals")
            for dog in animal_state["dogs"]:
                dog["patrol_index"] = (dog["patrol_index"]+1) % len(dog["patrol"])
                dog["position"] = list(dog["patrol"][dog["patrol_index"]])
            self.schedule(self.now+60, "animal_tick", None, 0)
        for aid in self.actors:
            self._check_fears(aid)

    def _life_inspection(self, actor):
        routine = actor.get("routine")
        actor["planned_steps"] = []
        if routine:
            for i, step in enumerate(routine["steps"]):
                actor["planned_steps"].append({**step, "label": self.rules.actions[step["kind"]]["label"],
                    "status": "completed" if i < routine["index"] else "next" if i == routine["index"] else "planned",
                    "target_name": self.objects[step["target_id"]]["name"]})
        actor["household_objects"] = [{"id": obj["id"], "name": obj["name"], "kind": obj["kind"], "daily": daily_state(obj)}
            for obj in self.objects.values() if obj.get("household_id") == actor["household_id"] and daily_state(obj)]
        actor["social_categories"] = psychology.social_category_definitions()
        return self._story_inspection(actor)
