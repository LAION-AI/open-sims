import random

import pytest

from living_world.speech import SpeechLibrary, choose_phrase


def test_catalog_is_large_short_colloquial_and_emoji_rich():
    library = SpeechLibrary()
    try:
        rows = library.db.execute("SELECT phrase FROM speech_phrases").fetchall()
        assert len(rows) >= 100
        assert all(1 <= len(phrase.split()) <= 5 for (phrase,) in rows)
        assert all(any(ord(ch) > 127 for ch in phrase) for (phrase,) in rows)
    finally:
        library.close()


def test_selection_is_seeded_and_varies_with_seed():
    library = SpeechLibrary()
    try:
        context = {"action_kind": "work", "job": "science"}
        a = [library.choose(context, random.Random(213)) for _ in range(1)]
        b = [library.choose(context, random.Random(213)) for _ in range(1)]
        varied = {library.choose(context, random.Random(seed)) for seed in range(20)}
        assert a == b
        assert len(varied) > 3
        assert all("🧪" in phrase or any(token in phrase for token in ("💪", "☕", "😅", "😎", "🎯", "🫠", "😬", "🌇")) for phrase in varied)
    finally:
        library.close()


def test_specific_situation_keys_cover_events_relationships_and_microtasks():
    library = SpeechLibrary()
    try:
        assert library.choose({"event": "hired"}, random.Random(1)) in {
            "Ich hab den Job! 🥳", "Neuer Anfang! 💼", "Das hat geklappt 🙌", "Erster Tag, los geht's ✨"
        }
        assert library.choose({"relationship": "spouse"}, random.Random(1)) in {
            "Schatz, wie war's? 💛", "Team wir zwei 🤝", "Ich hab dich lieb 🥰", "Abendessen zusammen? 🍝"
        }
        assert library.choose({"action": "microtask"}, random.Random(2)) in {
            "Erst mal sortieren 🗂️", "Wer hat das geändert? 👀", "Kurz nachmessen 📏", "Ich frag mal nach 💬",
            "Das fehlt noch 🧩", "Fast geschafft 🏁", "Uff, kompliziert 😵", "Sieht gut aus ✨"
        }
    finally:
        library.close()


def test_sql_context_is_not_interpolated_or_executed():
    library = SpeechLibrary()
    try:
        before = library.count()
        result = library.choose({"action": "work'; DROP TABLE speech_phrases; --"}, random.Random(3))
        assert result
        assert library.count() == before
    finally:
        library.close()


def test_persistent_database_is_safely_seeded_idempotently(tmp_path):
    db = tmp_path / "speech.sqlite3"
    first = SpeechLibrary(db)
    count = first.count()
    first.close()
    second = SpeechLibrary(db)
    try:
        assert second.count() == count
        assert second.choose({"event": "baby_news"}, random.Random(12))
    finally:
        second.close()


def test_rng_required_and_one_off_api_has_no_network_dependency():
    with pytest.raises(ValueError):
        choose_phrase({"action": "party"})
    phrase = choose_phrase({"action": "party"}, random.Random(4))
    assert 1 <= len(phrase.split()) <= 5
