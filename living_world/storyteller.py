"""Seeded, action-grounded incidents for fictional residents.

An incident is sampled only when its witnessed trigger *completes*.  The
coordinator commits the action, consequence and narration in one Beat.  This
module never invents an off-screen trip or silently rewrites a relationship.
"""
from __future__ import annotations

from copy import deepcopy


INCIDENTS = (
    {"id": "work_bonus", "triggers": ("work",), "chance": .028,
     "text": "A supervisor praised the finished shift and paid a small bonus.",
     "money": 32, "needs": {"fun": -.08, "social": -.03}, "ambition": "career"},
    {"id": "work_repair", "triggers": ("work",), "chance": .018,
     "text": "A damaged work tool had to be replaced after the shift.",
     "money": -24, "needs": {"comfort": .10, "fun": .06}, "ambition": None},
    {"id": "community_prize", "triggers": ("community_meet",), "chance": .035,
     "text": "At the community desk, a volunteer handed over a local raffle prize.",
     "money": 45, "needs": {"fun": -.13}, "ambition": "community"},
    {"id": "community_disappointment", "triggers": ("community_meet",), "chance": .026,
     "text": "The community desk announced that a hoped-for event had been cancelled.",
     "money": 0, "needs": {"fun": .10, "social": .04}, "ambition": None},
    {"id": "clinic_bill", "triggers": ("visit_clinic",), "chance": .055,
     "text": "The clinic receptionist explained an unexpected treatment charge.",
     "money": -18, "needs": {"comfort": .08}, "ambition": None},
    {"id": "grocery_refund", "triggers": ("buy_groceries",), "chance": .035,
     "text": "The checkout clerk refunded a spoiled grocery item.",
     "money": 12, "needs": {"comfort": -.04}, "ambition": None},
    {"id": "shopping_loss", "triggers": ("leisure_shop_for_fun",), "chance": .024,
     "text": "At the shop, a broken purchase could not be returned.",
     "money": -16, "needs": {"fun": .08, "comfort": .04}, "ambition": None},
    {"id": "shopping_voucher", "triggers": ("leisure_shop_for_fun",), "chance": .028,
     "text": "The shop's checkout handed over a surprise voucher.",
     "money": 15, "needs": {"fun": -.06}, "ambition": None},
    {"id": "checkout_error", "triggers": ("buy_groceries",), "chance": .022,
     "text": "The grocery receipt revealed an unrefundable pricing mistake.",
     "money": -9, "needs": {"comfort": .05}, "ambition": None},
    {"id": "pool_confidence", "triggers": ("visit_pool", "leisure_swim"), "chance": .045,
     "text": "A surprisingly good swim lifted their spirits at the pool.",
     "money": 0, "needs": {"fun": -.12, "comfort": -.05}, "ambition": "hobby"},
    {"id": "pool_slip", "triggers": ("visit_pool", "leisure_swim"), "chance": .012,
     "text": "A slip beside the pool spoiled the outing.",
     "money": 0, "needs": {"comfort": .12, "fun": .07}, "ambition": None},
    {"id": "gym_progress", "triggers": ("exercise_gym", "leisure_work_out"), "chance": .055,
     "text": "A difficult exercise finally went smoothly at the gym.",
     "money": 0, "needs": {"fun": -.10}, "ambition": "mastery"},
    {"id": "gym_strain", "triggers": ("exercise_gym", "leisure_work_out"), "chance": .018,
     "text": "Overdoing a set at the gym left them sore and annoyed.",
     "money": 0, "needs": {"comfort": .13, "fun": .05}, "ambition": None},
    {"id": "party_surprise", "triggers": ("leisure_host_party", "leisure_attend_party"), "chance": .048,
     "text": "An unexpected party game became the highlight of the gathering.",
     "money": 0, "needs": {"social": -.10, "fun": -.13}, "ambition": "community"},
    {"id": "party_cleanup", "triggers": ("leisure_host_party",), "chance": .023,
     "text": "A broken party decoration needed replacing after the guests left.",
     "money": -11, "needs": {"comfort": .08}, "ambition": None},
    {"id": "karaoke_applause", "triggers": ("leisure_karaoke",), "chance": .060,
     "text": "The karaoke performance drew a warm round of applause.",
     "money": 0, "needs": {"social": -.06, "fun": -.11}, "ambition": "community"},
    {"id": "karaoke_mishap", "triggers": ("leisure_karaoke",), "chance": .026,
     "text": "A microphone failure made the karaoke moment awkward.",
     "money": 0, "needs": {"fun": .08, "comfort": .05}, "ambition": None},
    {"id": "volunteer_thanks", "triggers": ("leisure_volunteer",), "chance": .060,
     "text": "A thank-you note at the volunteer desk recognized the effort.",
     "money": 0, "needs": {"social": -.09, "fun": -.05}, "ambition": "care"},
    {"id": "garden_bloom", "triggers": ("leisure_garden", "garden"), "chance": .045,
     "text": "A stubborn plant finally flowered during the gardening session.",
     "money": 0, "needs": {"fun": -.08, "comfort": -.06}, "ambition": "hobby"},
    {"id": "garden_pest", "triggers": ("leisure_garden", "garden"), "chance": .024,
     "text": "Pests damaged a favorite plant during the gardening session.",
     "money": 0, "needs": {"fun": .08}, "ambition": None},
    {"id": "game_winning_streak", "triggers": ("leisure_board_games", "leisure_video_games"), "chance": .050,
     "text": "A lucky streak made the game especially satisfying.",
     "money": 0, "needs": {"fun": -.09}, "ambition": "hobby"},
    {"id": "bar_promotion", "triggers": ("visit_bar",), "chance": .030,
     "text": "A house promotion at the bar made the visit unexpectedly cheerful.",
     "money": 0, "needs": {"fun": -.09}, "ambition": None},
    {"id": "club_awkward", "triggers": ("dance_club", "leisure_dance"), "chance": .023,
     "text": "A missed step on the dance floor drew an awkward glance.",
     "money": 0, "needs": {"fun": .07, "comfort": .04}, "ambition": None},
    {"id": "club_highlight", "triggers": ("dance_club", "leisure_dance"), "chance": .045,
     "text": "A favorite song on the dance floor made the night memorable.",
     "money": 0, "needs": {"fun": -.12, "social": -.04}, "ambition": "hobby"},
)


def incident_for(actor: dict, action: dict, rng) -> dict | None:
    """One bounded draw per completed activity; no action means no incident."""
    if actor.get("age", 18) < 18 and action["kind"] == "work":
        return None
    if action['kind']=='work' and actor.get('profile',{}).get('job')=='Unemployed':
        return None
    if actor.get("storyteller_last_day") == action["ends_at"] // 86400:
        return None
    options = [row for row in INCIDENTS if action["kind"] in row["triggers"]]
    draw = rng.random()
    for row in options:
        if draw < row["chance"]:
            return deepcopy(row)
        draw -= row["chance"]
    return None


def apply_incident(actor: dict, incident: dict, now: int, evidence_id: str, trigger_kind: str | None = None) -> int:
    """Call only inside the coordinator's completing-action transaction."""
    before=actor["money"]
    actor["money"] = max(0, before + incident["money"])
    for need, delta in incident["needs"].items():
        actor["needs"][need] = round(max(0, min(1, actor["needs"][need] + delta)), 4)
    actor["storyteller_last_day"] = now // 86400
    actor["last_story_incident"] = {"id": incident["id"], "at": now, "evidence_id": evidence_id,
                                    "trigger": trigger_kind or incident["triggers"][0], "text": incident["text"]}
    if incident["ambition"]:
        for goal in actor.get("psychology", {}).get("ambitions", []):
            if goal.get("kind") == incident["ambition"]:
                goal["progress"] = round(min(1, goal.get("progress", 0) + .08), 4)
                goal["updated_at"] = now
    actor["thought"] = {"text": incident["text"], "trigger": incident["id"], "since": now}
    return actor["money"]-before


def social_turn(actor: dict, other: dict, category: str, rng) -> dict | None:
    """A surprise is only eligible after both residents accepted a real chat."""
    ps = actor.get("psychology", {}).get("social_style", {})
    relation = actor.get("relations", {}).get(other["id"], {})
    tension = float(relation.get("tension", 0))
    if category == "gossip":
        subjects = [key for key in actor.get("relations", {}) if key != other["id"]]
        if subjects:
            subject = sorted(subjects)[int(rng.random() * len(subjects))]
            return {"kind": "rumor", "subject_id": subject,
                    "text": f"{actor['name']} told {other['name']} an uncertain story about {subject}."}
    if category == "undermine":
        backfire = rng.random() < .38 + (1 - float(ps.get("ruthlessness", .5))) * .10
        return {"kind": "sabotage_backfire" if backfire else "sabotage",
                "text": (f"{other['name']} noticed {actor['name']}'s attempt to make them look bad at work."
                         if backfire else f"{actor['name']} made {other['name']}'s work look worse during their exchange.")}
    if category == 'challenge':
        return {'kind':'friendly_rivalry',
                'text':f"{actor['name']} and {other['name']} enjoyed a spirited contest together."}
    if category in {"set_boundary", "gossip", "coordinate_work", "flirt"}:
        chance = .025 + tension * .28 + float(ps.get("competitiveness", .5)) * .035
        if rng.random() < chance:
            return {"kind": "argument", "text": f"A disagreement during {category.replace('_', ' ')} turned into an argument between {actor['name']} and {other['name']}."}
    if category == "offer_help" and rng.random() < .12:
        return {"kind": "unexpected_support", "text": f"{actor['name']} offered practical help and {other['name']} gratefully accepted."}
    return None


def remember_rumor(listener: dict, subject_id: str, speaker_id: str, now: int, evidence_id: str) -> None:
    """Hearsay creates uncertain knowledge, never a direct relationship edge."""
    heard = listener.setdefault("heard_of", {})
    heard[subject_id] = {"source_id": speaker_id, "at": now, "confidence": "low",
                         "evidence_id": evidence_id, "kind": "secondhand_story"}
    if len(heard) > 24:
        oldest = min(heard, key=lambda key: heard[key]["at"])
        del heard[oldest]


def adapt_style(actor: dict, event_kind: str) -> None:
    """Small bounded personality drift; bad experiences are not destiny."""
    style = actor.get("psychology", {}).get("social_style")
    if not style:
        return
    incident=next((row for row in INCIDENTS if row['id']==event_kind),None)
    adverse=bool(incident and (incident['money']<0 or sum(incident['needs'].values())>0))
    default=(.004,-.003) if adverse else (-.003,.003) if incident else (0,0)
    delta={"sabotage_backfire": (.012, -.008), "argument": (.006, -.006),
           "unexpected_support": (-.012, .018), "affection": (-.012, .014)}.get(event_kind,default)
    for key, amount in zip(("ruthlessness", "compassion"), delta):
        style[key] = round(max(0, min(1, style[key] + amount)), 4)


def social_status(actor: dict, population: dict | None = None) -> float:
    """Visible game standing from resources, career and *incoming* respect."""
    money = min(1, max(0, float(actor.get("money", 0))) / 700)
    career = actor.get("career", {})
    job = 0 if actor.get("profile", {}).get("job") in {"Unemployed", "Retired"} else .35
    job += min(.4, float(career.get("level", 0)) * .08)
    if population:
        edges=[other.get('relations', {}).get(actor['id']) for other in population.values()
               if other['id'] != actor['id'] and actor['id'] in other.get('relations', {})]
    else:
        edges=list(actor.get("relations", {}).values())
    regard = sum(float(row.get("respect", .35)) for row in edges) / max(1, len(edges))
    reach = min(1, len(edges) / 12)
    return round(max(0, min(1, .28 * money + .27 * job + .32 * regard + .13 * reach)), 4)


def group_dynamic(host: dict, companions: list[dict], rng) -> dict | None:
    """Propose one witnessed triadic turn after all members joined a real scene.

    The coordinator applies the returned pair consequence in the action Beat.
    This never creates off-screen meetings or overrides an invitation refusal.
    """
    if len(companions)<2:
        return None
    first,second=rng.sample(companions,2)
    edge=first.get('relations',{}).get(second['id'],{})
    reverse=second.get('relations',{}).get(first['id'],{})
    tension=(edge.get('tension',0)+reverse.get('tension',0))/2
    competition=(first.get('psychology',{}).get('social_style',{}).get('competitiveness',.4)
                 +second.get('psychology',{}).get('social_style',{}).get('competitiveness',.4))/2
    compassion=host.get('psychology',{}).get('social_style',{}).get('compassion',.5)
    chance=min(.46,.13+.22*tension+.13*competition)
    if rng.random()>=chance:
        return None
    awkward=rng.random()<min(.62,.12+.40*tension+.22*competition)
    if awkward:
        mediated=rng.random()<.08+.52*compassion
        kind='mediated_disagreement' if mediated else 'group_disagreement'
        outcome='neutral' if mediated else 'negative'
        text=(f"{first['name']} and {second['name']} disagreed in the group; "
              +(f"{host['name']} helped them slow down." if mediated else
                'the exchange left a little tension.'))
    else:
        kind='shared_joke'
        outcome='positive'
        text=f"{first['name']} and {second['name']} found common ground in a shared joke."
    return {'kind':kind,'first_id':first['id'],'second_id':second['id'],
            'outcome':outcome,'category':'check_in' if kind=='mediated_disagreement' else 'tell_joke',
            'text':text,'host_id':host['id']}
