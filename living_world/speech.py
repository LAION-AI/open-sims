"""Short, local speech bubbles for the living world.

The catalog is seeded into SQLite on construction, so a fresh install has no
binary database artifact and no network/model dependency. Selection is pure
with respect to the simulation: it reads the catalog and the caller supplies
the RNG, while the world coordinator remains responsible for any state change.
"""
from __future__ import annotations

import random
import sqlite3
from pathlib import Path
from typing import Any


# Each row is (phrase, dimension, key). The wildcard dimensions are intentional
# fallback material, not random generated text.
_PHRASES: list[tuple[str, str, str]] = []


def _add(dimension: str, key: str, *phrases: str) -> None:
    for phrase in phrases:
        words = phrase.split()
        # Keep the last token (the expressive emoji) while bounding the bubble.
        if len(words) > 5:
            phrase = ' '.join(words[:4] + [words[-1]])
        _PHRASES.append((phrase, dimension, key))


_add("action", "work", "Ich pack das 💪", "Kaffee rettet mich ☕", "Noch kurz durchziehen 😅", "Das läuft ja 😎", "Fokus, bitte 🎯", "Pause wär schön 🫠", "Bloß kein Meeting 😬", "Feierabend in Sicht 🌇")
_add("action", "project", "Wo war ich? 🤔", "Plan steht! 🗒️", "Das wird was ✨", "Kleine Krise 😵", "Fix ich gleich 🔧", "Bitte speichern 💾", "Läuft… meistens 😅", "Noch ein Versuch 🧪", "Teamwork, Leute 🤝", "Das ging schief 🙃")
_add("action", "mic_task", "Erst mal sortieren 🗂️", "Wer hat das geändert? 👀", "Kurz nachmessen 📏", "Ich frag mal nach 💬", "Das fehlt noch 🧩", "Fast geschafft 🏁", "Uff, kompliziert 😵", "Sieht gut aus ✨")
_add("action", "party", "Musik lauter! 🎶", "Das ist mein Song 💃", "Noch ein Tanz? 🪩", "Was für ein Abend ✨", "Ich hol Snacks 🍿", "Alle sind da! 🥳", "Wer legt auf? 🎧", "Nur noch ein Lied 😄")
_add("action", "date", "Du siehst toll aus 😊", "Das ist echt schön 💛", "Noch einen Kaffee? ☕", "Ich bin gern hier 🥰", "War das ein Flirt? 😏", "Erzähl mir mehr ✨", "Nervös? Ein bisschen 😅", "Wiedersehen wär schön 💌")
_add("action", "argument", "Jetzt hör mir zu! 😠", "Das war nicht okay 😤", "Lass mich ausreden 🙄", "Wir reden später 😮‍💨", "Das eskaliert gerade 😬", "Tut mir leid 😔", "Ich brauch Abstand 🫥", "War nicht so gemeint 😣")
_add("action", "kiss", "Komm näher 😘", "Darf ich? 💕", "Oh, wow 🥰", "Noch mal? 😚", "Das war schön 💗", "Du bist süß 😊")
_add("action", "relax", "Heute ganz langsam 🛋️", "Nichts muss jetzt 🌿", "Das tut gut 😌", "Einfach mal sein ☁️", "Akku lädt 🔋", "Bitte keine Termine 😴")
_add("action", "hobby", "Das macht Spaß! 🎨", "Nur noch kurz 😄", "Voll mein Ding ✨", "Schau mal hier 👀", "Das probier ich! 🧶", "Kreativmodus an 🎨", "Zeit vergessen 😅", "Richtig gemütlich 📚")
_add("action", "exercise", "Noch eine Runde 🏃", "Ich spür's schon 😅", "Frische Luft! 🌤️", "Geschafft! 💪", "Das tat gut 🏋️", "Langsam reicht's 😮‍💨")
_add("action", "care", "Ich bin für dich da 💛", "Brauchst du was? 🫶", "Alles okay bei dir? 💬", "Zusammen schaffen wir's 🤝", "Ich helf dir gern 🌷")

_add("social", "greet", "Na, alles klar? 👋", "Hey, schön dich zu sehen 😊", "Was geht? 😄", "Lange nicht gesehen! ✨", "Moin! ☀️", "Hi du! 👋")
_add("social", "joke", "Okay, der war gut 😂", "Ich kann nicht mehr 🤣", "Flach, aber lustig 😅", "Erzähl noch einen! 😄")
_add("social", "gossip", "Hast du das gehört? 👀", "Unter uns gesagt 🤫", "Schon ein bisschen wild 😳", "Ich sag ja nur 😅")
_add("social", "invite", "Kommst du mit? 🎉", "Lust auf was Schönes? 🌟", "Heute Abend frei? 👀", "Sei dabei! 🥳", "Zusammen macht's mehr Spaß 🤝")
_add("social", "compliment", "Du hast tolle Energie ✨", "Steht dir richtig gut 😍", "Du bist echt klasse 💛", "Mit dir wird's nie langweilig 😄")
_add("social", "flirt", "Na, öfter hier? 😉", "Du gefällst mir 😏", "Ist das ein Date? 💘", "Dein Lächeln! 😊", "Ich mag deine Art 💕")
_add("social", "comfort", "Das klingt echt schwer 😔", "Ich hör dir zu 🫶", "Du bist nicht allein 💛", "Lass dir Zeit 🌿")
_add("social", "apology", "War mein Fehler 😔", "Sorry, echt jetzt 🙏", "Können wir reden? 💬", "Ich mach's wieder gut 🌷")
_add("social", "confront", "Das sehe ich anders 😐", "Reden wir ruhig 😮‍💨", "Stopp, das verletzt 😣", "Nicht vor allen 😤")

_add("affect", "joy", "Das macht mich happy 😄", "Heute läuft's! ✨", "Ich könnt platzen 🥳", "Was für ein Glück 🍀", "Yesss! 🙌")
_add("affect", "sad", "Heute ist's schwer 😔", "Ich brauch kurz Ruhe 🌧️", "Nicht mein Tag 🫥", "Morgen wird besser 🌱")
_add("affect", "angry", "Ich bin echt sauer 😠", "Jetzt reicht's 😤", "Lass mich kurz 😡", "Das nervt total 🙄")
_add("affect", "anxious", "Bin etwas nervös 😬", "Was, wenn's schiefgeht? 😟", "Einmal tief atmen 🌬️", "Ich schaff das schon 💛")
_add("affect", "tired", "Ich bin durch 😴", "Akku bei zwei Prozent 🪫", "Zeit fürs Bett 🛌", "Nur noch heim 🥱")
_add("affect", "romantic", "Du fehlst mir 💌", "Ganz nah bei dir 💕", "Mein Lieblingsmensch 🥰", "Das kribbelt ✨", "Nur wir zwei 💗")
_add("affect", "bored", "Irgendwas muss passieren 🥱", "Mir ist so öde 😑", "Spontan was starten? 👀", "Netflix und Snacks? 🍿")

_add("relationship", "spouse", "Schatz, wie war's? 💛", "Team wir zwei 🤝", "Ich hab dich lieb 🥰", "Abendessen zusammen? 🍝")
_add("relationship", "friend", "Besties for life 😎", "Mit dir immer gern 💛", "Unser nächstes Abenteuer? 🗺️", "Du bist Gold wert ✨")
_add("relationship", "coworker", "Gutes Team heute 🤝", "Danke fürs Mitdenken 🙌", "Kaffee zusammen? ☕", "Stark gelöst! 💪")
_add("relationship", "family", "Familienzeit 💛", "Ich pass auf dich auf 🫶", "Komm gut heim 🌙", "Hab dich lieb 😊")
_add("relationship", "rival", "Na, schon wieder du? 😏", "Diesmal gewinn ich 😤", "Gönn ich dir… fast 😅", "Wir sprechen noch 😎")
_add("relationship", "stranger", "Darf ich kurz? 👋", "Kenn ich dich? 🤔", "Schönen Tag noch ☀️", "Hi, ich bin neu 😊")

_add("job", "office", "Inbox bezwungen 📧", "Das Meeting zieht sich 😵", "Zahlen lügen nicht 📊", "Ab an die Tabelle 📈", "Kalender sagt nein 🗓️", "Mail ist raus ✉️")
_add("job", "science", "Probe ist bereit 🧪", "Daten sehen spannend aus 🔬", "Hypothese wackelt 🤔", "Bitte nichts verschütten 😅", "Fundstück entdeckt! 🧬")
_add("job", "healthcare", "Nächster Fall, bitte 🩺", "Alles gut versorgt 💛", "Kurz Hände waschen 🧼", "Teamwork hilft 🏥", "Schicht geschafft! 🌙")
_add("job", "education", "Alle aufgepasst 👩‍🏫", "Fragen sind willkommen 💬", "Hausaufgaben nicht vergessen 📚", "Heute lief die Stunde ✨", "Kreide alle 😅")
_add("job", "service", "Gleich bin ich da 👋", "Danke fürs Warten 😊", "Noch eine Bestellung 🍽️", "Trinkgeld wär nett 😅", "Schichtende in Sicht 🌇")
_add("job", "creative", "Idee auf Papier ✍️", "Das braucht Farbe 🎨", "Kreativchaos pur 😅", "Fast ein Meisterwerk ✨", "Bitte nicht löschen 💾")
_add("job", "trades", "Werkzeug sitzt 🔧", "Maß nehmen, los 📏", "Das hält bombenfest 💪", "Wo ist der Schlüssel? 🔩", "Saubere Arbeit ✨")
_add("job", "culinary", "Noch etwas Salz 🧂", "Pfanne heiß! 🍳", "Bestellung ist raus 🍲", "Küche im Flow 🔥", "Bitte nicht anbrennen 😬")
_add("job", "public_safety", "Lage ist ruhig 🚓", "Wir bleiben wachsam 👀", "Alles unter Kontrolle 💪", "Funkgerät knistert 📻", "Sicher nach Hause 🌙")
_add("job", "unemployed", "Heute such ich was 💼", "Bewerbung ist raus ✉️", "Neuer Start, neues Glück 🍀", "Erst mal durchschnaufen 🌿", "Ich bleib dran 💪")

_add("event", "hired", "Ich hab den Job! 🥳", "Neuer Anfang! 💼", "Das hat geklappt 🙌", "Erster Tag, los geht's ✨")
_add("event", "fired", "Das kam unerwartet 😳", "Okay, Neustart 🌱", "Ich brauch kurz Zeit 😔", "Weiter geht's irgendwann 💛")
_add("event", "promotion", "Beförderung! 🥳", "Einsatz zahlt sich aus 💪", "Eine Stufe höher 🚀", "Heute wird gefeiert 🎉")
_add("event", "failure", "Uff, knapp daneben 😬", "Das lief schief 🙃", "Okay, Plan B 🤔", "Nächstes Mal klappt's 💪", "Wer räumt das auf? 😅")
_add("event", "party_started", "Die Party läuft! 🥳", "Alle herkommen! 🎉", "Playlist ist bereit 🎶", "Snacks stehen da 🍕")
_add("event", "date_accepted", "Es ist ein Date! 💘", "Oh wow, ja! 🥰", "Ich freu mich schon ✨", "Das wird schön 💕")
_add("event", "date_rejected", "Alles gut, ehrlich 🙂", "Danke fürs Klarsein 💛", "Kein Druck 😊", "Freunde bleiben? 🌿")
_add("event", "fight", "Jetzt ist Schluss! 😠", "Geh mir aus dem Weg 😤", "Ruf Hilfe! 😨", "Das reicht jetzt! 🛑")
_add("event", "reconcile", "Frieden? 🤝", "Neustart zusammen 🌱", "Ich verzeih dir 💛", "Lass es gut sein 🌿")
_add("event", "baby_news", "Wir werden Eltern! 🥹", "Da kommt ein Baby 🍼", "Kleines Wunder unterwegs 💛", "Familie wächst! 🌱")

_add("generic", "*", "Na dann, los geht's! ✨", "Mal sehen, was kommt 👀", "Das wird schon 😌", "Klingt nach einem Plan 👍", "Kurz durchatmen 🌬️", "Heute ist was los 😄", "Weiter geht's 💪", "Ach, herrlich 😅", "Das Leben eben 🌿", "Ich bin dabei 🙌", "Echt jetzt? 😳", "Unerwartet, aber okay 🤷")


def _validate_catalog() -> None:
    for phrase, _, _ in _PHRASES:
        words = phrase.split()
        if not 1 <= len(words) <= 5 or not any(ord(c) > 127 for c in phrase):
            raise RuntimeError(f"Invalid bubble phrase: {phrase!r}")


_validate_catalog()


class SpeechLibrary:
    """SQLite phrase store and deterministic selector.

    ``choose(context, rng)`` reads the most specific matching phrase group.
    Context values are categorical keys only; they are never interpolated into
    output. The injected ``random.Random`` (or compatible ``choice`` RNG) makes
    repeats reproducible and leaves global randomness untouched.
    """

    def __init__(self, database: str | Path = ":memory:"):
        if str(database) != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(database))
        self.db.execute("""CREATE TABLE IF NOT EXISTS speech_phrases (
            id INTEGER PRIMARY KEY, phrase TEXT NOT NULL, dimension TEXT NOT NULL,
            phrase_key TEXT NOT NULL, UNIQUE(phrase, dimension, phrase_key))""")
        self.db.executemany("INSERT OR IGNORE INTO speech_phrases(phrase,dimension,phrase_key) VALUES(?,?,?)", _PHRASES)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    @staticmethod
    def _keys(context: dict[str, Any]) -> list[tuple[str, str]]:
        # Earlier tuples have higher specificity. We accept the canonical
        # dimension names plus small aliases that make coordinator integration easy.
        action = str(context.get("action_kind", context.get("action", ""))).casefold()
        social = str(context.get("social_category", context.get("social", ""))).casefold()
        affect = str(context.get("affect", context.get("mood", ""))).casefold()
        relation = str(context.get("relationship", context.get("relation", ""))).casefold()
        job = str(context.get("job", context.get("job_category", ""))).casefold()
        event = str(context.get("event", "")).casefold()
        keys: list[tuple[str, str]] = []
        if event: keys.append(("event", event))
        if action: keys.append(("action", action))
        if social: keys.append(("social", social))
        if job: keys.append(("job", job))
        if relation: keys.append(("relationship", relation))
        if affect: keys.append(("affect", affect))
        # Affective family fallbacks support common stat vocabularies.
        if affect in {"happy", "excited", "playful", "content", "positive"}: keys.append(("affect", "joy"))
        if affect in {"sadness", "lonely", "grief", "negative"}: keys.append(("affect", "sad"))
        if affect in {"anger", "frustrated", "hostile"}: keys.append(("affect", "angry"))
        if action in {"working_on_project", "work_project"}: keys.append(("action", "project"))
        if action in {"party", "dance", "celebrate"}: keys.append(("action", "party"))
        if action in {"date", "ask_date", "dating"}: keys.append(("action", "date"))
        if action in {"kiss", "make_out", "romantic_kiss"}: keys.append(("action", "kiss"))
        if action in {"argue", "shout", "fight", "quarrel"}: keys.append(("action", "argument"))
        if action in {"work_microtask", "microtask", "project_task"}: keys.append(("action", "mic_task"))
        if action in {"hobby", "read", "craft", "garden", "cook", "fishing", "painting", "play_game"}: keys.append(("action", "hobby"))
        # Preserve precedence and avoid repeated queries.
        return list(dict.fromkeys(keys))

    def choose(self, context: dict[str, Any] | None = None, rng=None) -> str:
        """Return one short bubble, using context-specific phrases when present."""
        if rng is None:
            raise ValueError("Pass a seeded RNG to choose()")
        if not hasattr(rng, "choice"):
            raise TypeError("rng must provide choice()")
        context = context or {}
        for dimension, key in self._keys(context):
            rows = self.db.execute(
                "SELECT phrase FROM speech_phrases WHERE dimension=? AND phrase_key=? ORDER BY id",
                (dimension, key),
            ).fetchall()
            if rows:
                return rng.choice([row[0] for row in rows])
        rows = self.db.execute("SELECT phrase FROM speech_phrases WHERE dimension='generic' ORDER BY id").fetchall()
        return rng.choice([row[0] for row in rows])

    def count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM speech_phrases").fetchone()[0])


def choose_phrase(context: dict[str, Any] | None = None, rng=None,
                  database: str | Path = ":memory:") -> str:
    """Convenience API for one-off use; long-lived coordinators should reuse a library."""
    if rng is None:
        raise ValueError("Pass a seeded RNG to choose_phrase()")
    library = SpeechLibrary(database)
    try:
        return library.choose(context, rng)
    finally:
        library.close()
