"""Pure, seeded work-shift and employment event models.

The coordinator owns all state changes. This module only describes a shift or
returns proposals; callers decide whether and when to apply any result.
"""
from __future__ import annotations

from copy import deepcopy
import random

from .careers import CAREERS


# Each profession gets its own palette of short, concrete work activities.
PROFESSION_TASKS = {
    "Teacher": ("Plan tomorrow's lesson", "Explain fractions", "Mark homework", "Calm a noisy class", "Help a shy student", "Find the missing glue"),
    "Illustrator": ("Thumbnail a new scene", "Ink a character", "Choose a color palette", "Fix a wonky hand", "Send a client preview", "Polish the final page"),
    "Designer": ("Sketch three layouts", "Review a color system", "Pitch a concept", "Revise client feedback", "Check a prototype", "Prep a handoff"),
    "Carpenter": ("Measure a cabinet panel", "Cut clean joints", "Sand a rough edge", "Fit a stubborn hinge", "Check the level", "Sweep the sawdust"),
    "Tailor": ("Take a jacket fitting", "Cut the lining", "Thread the old machine", "Sew a neat hem", "Replace a loose button", "Steam the finished coat"),
    "Gardener": ("Prune the rose beds", "Water thirsty seedlings", "Test the soil", "Chase off hungry pigeons", "Plant a new border", "Compost fallen leaves"),
    "Baker": ("Mix the sourdough", "Shape today's rolls", "Rescue an overproofed batch", "Ice the cake display", "Serve the morning rush", "Clean the floury counter"),
    "Bookseller": ("Recommend a page-turner", "Restock the mystery shelf", "Unpack a book delivery", "Set up a reading display", "Find a special order", "Settle a till question"),
    "Nurse": ("Check a patient's chart", "Prep a clean bed", "Reassure a nervous visitor", "Coordinate a handoff", "Restock the treatment cart", "Call the next patient"),
    "Firefighter": ("Inspect breathing gear", "Practice hose coupling", "Check the dispatch board", "Run a ladder drill", "Repack the first-aid kit", "Polish the engine bay"),
    "Civic clerk": ("Sort permit requests", "Explain a form", "Check a resident's record", "Find a misplaced folder", "Book a public appointment", "Untangle a printer jam"),
    "Office analyst": ("Clean a messy spreadsheet", "Check the weekly forecast", "Explain an odd data spike", "Compare two reports", "Build a clear chart", "Answer a teammate's question"),
    "Fitness coach": ("Plan a gentle warmup", "Coach a squat set", "Count a group circuit", "Encourage a tired member", "Wipe down the mats", "Adjust someone's training plan"),
    "Retail assistant": ("Restock the front shelf", "Help a customer choose", "Check a price mismatch", "Open another checkout", "Unpack a delivery", "Recover a dropped display"),
    "Independent artist": ("Lay out a fresh canvas", "Try a risky color mix", "Photograph finished work", "Answer a commission note", "Tidy the studio table", "Make one brave revision"),
    "Physician": ("Review a clinic case", "Explain a care plan", "Consult a colleague", "Check a test result", "Update patient notes", "Take a careful history"),
    "Chef": ("Prep the lunch vegetables", "Taste and adjust the sauce", "Call a ticket to the line", "Rescue a salty soup", "Plate the special", "Coordinate the pass"),
    "Mechanic": ("Diagnose a rattling engine", "Replace a worn belt", "Find the missing socket", "Test the repaired brakes", "Explain a repair estimate", "Clean the work bay"),
    "Programmer": ("Trace a stubborn bug", "Review a teammate's code", "Ship a tiny feature", "Write a test case", "Explain an API change", "Undo a risky commit"),
    "Civic planner": ("Review a street proposal", "Map a safer crossing", "Hear a resident's concern", "Compare zoning options", "Revise a park plan", "Present a clear tradeoff"),
    "Kindergarten educator": ("Welcome the little ones", "Read a picture book", "Guide a painting table", "Settle a playground dispute", "Prepare a snack", "Share pickup notes"),
    "Lifeguard": ("Watch the shallow end", "Check the pool water", "Teach a safety rule", "Help a new swimmer", "Inspect the rescue gear", "Clear a slippery spot"),
    "Bartender": ("Mix a house special", "Serve a quiet regular", "Restock the glasses", "Wipe the bar", "Handle a busy round", "Check an ID"),
    "Club DJ": ("Build the evening playlist", "Cue the next track", "Read the dance floor", "Fix a stubborn speaker", "Take a song request", "Close the set"),
    "Professor": ("Prepare a lecture example", "Lead a seminar debate", "Answer a student's question", "Mark a research essay", "Discuss a thesis plan", "Update the course notes"),
    "Researcher": ("Calibrate a lab instrument", "Run a controlled experiment", "Check an unexpected result", "Document a sample", "Review a colleague's method", "Prepare a research briefing"),
    "University administrator": ("Process a course registration", "Plan a room timetable", "Help a visiting student", "Resolve a booking clash", "Update a campus notice", "Coordinate a faculty request"),
}

_COLLAB = ("coordinate", "offer_help", "ask_advice", "share_credit", "small_talk", "disagree")
_MISHAPS = ("small_error", "equipment_glitch", "miscommunication", "lucky_break")
_clamp = lambda n, lo=0.0, hi=1.0: max(lo, min(hi, float(n)))


def _rng(seed_or_rng):
    if isinstance(seed_or_rng, int):
        return random.Random(seed_or_rng)
    if seed_or_rng is None or not all(hasattr(seed_or_rng, name) for name in ("random", "choice")):
        raise TypeError("pass an integer seed or Random-compatible RNG")
    return seed_or_rng


def build_shift_plan(actor, coworkers=(), duration_seconds=4 * 3600, seed=0):
    """Return a reproducible sequence of profession microtasks and social openings.

    Coworkers may be actor dictionaries or ids. Each step is capped at 45 min;
    final duration never exceeds the requested (nonnegative) shift length.
    """
    job = actor.get("profile", {}).get("job") or (actor.get("career") or {}).get("job") or "Independent artist"
    job = job if job in PROFESSION_TASKS else "Independent artist"
    rng = _rng(seed)
    total = max(0, int(duration_seconds))
    people = [p.get("id") if isinstance(p, dict) else str(p) for p in coworkers]
    steps, elapsed = [], 0
    while elapsed < total:
        duration = min(total - elapsed, rng.randint(15, 45) * 60)
        steps.append({"index": len(steps), "profession": job, "task": rng.choice(PROFESSION_TASKS[job]),
                      "duration_seconds": duration,
                      "colleague_id": rng.choice(people) if people else None,
                      "interaction_options": list(_COLLAB) if people else [],
                      "interaction_probability": round(_clamp(.12 + .55 * float(actor.get("psychology", {}).get("big_five", {}).get("extraversion", .5)), .04, .82), 3),
                      "mishap_probability": round(_clamp(.025 + .04 * (1-float(actor.get("psychology", {}).get("big_five", {}).get("conscientiousness", .5))), .01, .09), 3)})
        elapsed += duration
    return {"profession": job, "duration_seconds": total, "steps": steps, "seeded": True}


def resolve_work_step(actor, step, seed=0):
    """Resolve one task to an interaction/mishap and bounded performance delta."""
    rng = _rng(seed)
    traits = actor.get("psychology", {}).get("big_five", {})
    conscientiousness = _clamp(traits.get("conscientiousness", .5))
    extraversion = _clamp(traits.get("extraversion", .5))
    options = step.get("interaction_options", [])
    interaction = None
    if options and rng.random() < _clamp(step.get("interaction_probability", .35)):
        interaction = rng.choice(options)
    mishap = None
    if rng.random() < _clamp(step.get("mishap_probability", .04), 0, .15):
        mishap = rng.choices(_MISHAPS, weights=(.42, .23, .28, .07), k=1)[0]
    base = .012 * (conscientiousness - .5) + .003 * (extraversion - .5)
    effect = {"small_error": -.055, "equipment_glitch": -.035, "miscommunication": -.045, "lucky_break": .035}.get(mishap, 0)
    if interaction in ("offer_help", "coordinate", "share_credit"):
        effect += .012
    elif interaction == "disagree":
        effect -= .006
    return {"task": str(step.get("task", "Work task")), "interaction": interaction,
            "colleague_id": step.get("colleague_id") if interaction else None,
            "mishap": mishap, "performance_delta": round(_clamp(base + effect, -.08, .05), 4),
            "fun_delta": round(_clamp(.012 + .012 * extraversion + (.018 if interaction in ("small_talk", "share_credit") else 0) - (.012 if mishap else 0), -.04, .05), 4)}


def search_jobs(actor, openings=None, seed=0, limit=5):
    """Return possible applications with personality/skill influenced success odds."""
    rng = _rng(seed)
    current = actor.get("profile", {}).get("job")
    candidates = list(openings if openings is not None else CAREERS)
    traits = actor.get("psychology", {}).get("big_five", {})
    skills = actor.get("skills", {})
    out = []
    for job in candidates:
        if job not in CAREERS or job == current:
            continue
        skill = CAREERS[job][0]
        fit = _clamp(skills.get(skill, .15))
        openness = _clamp(traits.get("openness", .5))
        conscientiousness = _clamp(traits.get("conscientiousness", .5))
        base = _clamp(.32 + .36 * fit + .18 * conscientiousness + .08 * openness, .08, .88)
        roll = rng.random()
        out.append({"job": job, "skill": skill, "fit": round(fit, 3), "success_probability": round(base, 3),
                    "outcome": "interview" if roll < base else "no_response" if roll > base + .19 else "declined",
                    "pay_factor": CAREERS[job][2]})
    return sorted(out, key=lambda row: (-row["success_probability"], row["job"]))[:max(0, int(limit))]


def evaluate_job_security(actor, shift_performance=None, seed=0):
    """Suggest a rare warning/dismissal event; does not change employment state."""
    rng = _rng(seed)
    career = actor.get("career") or {}
    performance = _clamp(career.get("performance", .5) if shift_performance is None else shift_performance)
    # Dismissal remains possible after a terrible shift but rare; solid workers
    # still face occasional bad luck such as restructuring.
    p = _clamp(.004 + max(0, .42-performance) * .12, .002, .055)
    draw = rng.random()
    return {"event": "fired" if draw < p * .22 else "job_warning" if draw < p else "none",
            "probability": round(p, 4), "performance": round(performance, 4),
            "next_job": None, "requires_coordinator_application": True}


def evaluate_hire(actor, job, seed=0):
    """Return a hire proposal for a specific open role, without applying it."""
    rng = _rng(seed)
    if job not in CAREERS:
        raise ValueError("unknown profession")
    skill = CAREERS[job][0]
    fit = _clamp(actor.get("skills", {}).get(skill, .15))
    conscientiousness = _clamp(actor.get("psychology", {}).get("big_five", {}).get("conscientiousness", .5))
    chance = _clamp(.28 + .42 * fit + .2 * conscientiousness, .12, .88)
    hired = rng.random() < chance
    return {"event": "hired" if hired else "application_declined", "job": job if hired else None,
            "probability": round(chance, 3), "requires_coordinator_application": True}
