import random

import pytest

from living_world.careers import CAREERS
from living_world.work_life import (
    PROFESSION_TASKS, build_shift_plan, evaluate_hire, evaluate_job_security,
    resolve_work_step, search_jobs,
)


def actor(job):
    return {"id": "sim-a", "profile": {"job": job}, "career": {"job": job, "performance": .5},
            "skills": {"craft": .4, "analysis": .7},
            "psychology": {"big_five": {"openness": .6, "conscientiousness": .7,
                                          "extraversion": .65, "agreeableness": .5, "neuroticism": .4}}}


@pytest.mark.parametrize("job", CAREERS)
def test_every_career_has_a_varied_bounded_plan(job):
    sim = actor(job)
    plan = build_shift_plan(sim, ["coworker"], 3 * 3600, seed=91)
    assert len(PROFESSION_TASKS[job]) >= 5
    assert plan == build_shift_plan(sim, ["coworker"], 3 * 3600, seed=91)
    assert sum(step["duration_seconds"] for step in plan["steps"]) == 3 * 3600
    assert all(0 < step["duration_seconds"] <= 45 * 60 for step in plan["steps"])
    assert all(step["colleague_id"] == "coworker" and step["interaction_options"] for step in plan["steps"])
    assert all(0 <= step["mishap_probability"] <= .09 for step in plan["steps"])


def test_empty_shift_and_missing_coworkers_are_safe():
    plan = build_shift_plan(actor("Teacher"), duration_seconds=-10, seed=0)
    assert plan["steps"] == [] and plan["duration_seconds"] == 0
    plan = build_shift_plan(actor("Teacher"), duration_seconds=60, seed=0)
    assert plan["steps"][0]["colleague_id"] is None
    assert resolve_work_step(actor("Teacher"), plan["steps"][0], seed=0)["colleague_id"] is None


def test_step_resolution_is_seeded_bounded_and_does_not_mutate_actor():
    sim = actor("Programmer")
    before = repr(sim)
    step = build_shift_plan(sim, ["b"], 1800, 12)["steps"][0]
    one = resolve_work_step(sim, step, 15)
    assert one == resolve_work_step(sim, step, 15)
    assert -.08 <= one["performance_delta"] <= .05
    assert -.04 <= one["fun_delta"] <= .05
    assert repr(sim) == before
    assert one["mishap"] in (None, "small_error", "equipment_glitch", "miscommunication", "lucky_break")


def test_job_search_and_hire_are_proposals_not_mutations():
    sim = actor("Teacher")
    before = repr(sim)
    rows = search_jobs(sim, seed=40)
    assert rows and all(row["job"] != "Teacher" for row in rows)
    assert all(0 <= row["success_probability"] <= 1 for row in rows)
    assert rows == search_jobs(sim, seed=40)
    assert evaluate_hire(sim, "Programmer", seed=4) == evaluate_hire(sim, "Programmer", seed=4)
    assert repr(sim) == before
    with pytest.raises(ValueError):
        evaluate_hire(sim, "Dragon tamer", seed=1)


def test_employment_security_stays_rare_and_can_propose_firing():
    sim = actor("Teacher")
    assert evaluate_job_security(sim, seed=5) == evaluate_job_security(sim, seed=5)
    assert evaluate_job_security(sim, shift_performance=1, seed=5)["probability"] <= .004
    outcomes = [evaluate_job_security(sim, shift_performance=0, seed=i)["event"] for i in range(5000)]
    assert "fired" in outcomes
    assert "job_warning" in outcomes
    assert "none" in outcomes


def test_accepts_random_compatible_injected_rng():
    assert build_shift_plan(actor("Baker"), seed=random.Random(3)) == build_shift_plan(actor("Baker"), seed=random.Random(3))
