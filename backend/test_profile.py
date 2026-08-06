"""Self-check for the student profile ACE learns from conversation.

Runs against a throwaway SQLite file — never touches the real DB. The LLM
extraction call is stubbed, so this is free and deterministic; what it checks is
the gating, merging, and storage around it.

    python -m backend.test_profile
"""

import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.mkdtemp(), "test_profile.db"
)

from backend.database import engine, Base, SessionLocal  # noqa: E402
from backend.models import User  # noqa: E402
from backend.services import profile_service as ps  # noqa: E402

Base.metadata.create_all(bind=engine)

USER = "user_profile_1"


def _seed():
    db = SessionLocal()
    try:
        if not db.get(User, USER):
            db.add(User(id=USER, selected_major="Computer Science, B.S. (Engineering)"))
            db.commit()
    finally:
        db.close()


def test_gate_skips_ordinary_questions():
    # Most messages say nothing personal. The gate is what keeps ACE from paying
    # for an extraction call on every single question.
    for q in [
        "what math courses are required for my major?",
        "when is the last day to drop?",
        "how do I register for classes?",
        "",
    ]:
        assert ps.extract_signals(q) == {}, f"gate should skip: {q!r}"


def test_gate_opens_on_personal_statements(monkeypatched=None):
    called = {}

    def fake_chat(messages, **kwargs):
        called["yes"] = True
        return '{"interests": ["dancing"], "career_goals": ["machine learning"]}'

    from backend.services import llm
    original = llm.chat
    llm.chat = fake_chat
    try:
        got = ps.extract_signals("I'm interested in dancing and I want to work in AI")
        assert called.get("yes"), "a personal statement must reach the extractor"
        assert got["interests"] == ["dancing"]
        assert got["career_goals"] == ["machine learning"]
    finally:
        llm.chat = original


def test_remember_merges_without_duplicating():
    _seed()
    from backend.services import llm
    original = llm.chat

    def reply(payload):
        return lambda messages, **kw: payload

    try:
        llm.chat = reply('{"interests": ["dancing"], "career_goals": ["machine learning"]}')
        p = ps.remember(USER, "I love dancing and I want to work in machine learning")
        assert p["interests"] == ["dancing"]

        # Same interest again, different casing — must not duplicate.
        llm.chat = reply('{"interests": ["Dancing", "hackathons"], "career_goals": []}')
        p = ps.remember(USER, "I'm into Dancing and hackathons")
        assert p["interests"] == ["dancing", "hackathons"], p["interests"]
        assert p["career_goals"] == ["machine learning"], "existing goals must survive"
    finally:
        llm.chat = original


def test_remember_is_never_load_bearing():
    _seed()
    from backend.services import llm
    original = llm.chat

    def boom(messages, **kw):
        raise RuntimeError("provider down")

    try:
        llm.chat = boom
        # A failed extraction must return None, not raise — the student already
        # has their answer on screen by the time this runs.
        assert ps.remember(USER, "I love dancing") is None
    finally:
        llm.chat = original

    assert ps.remember(None, "I love dancing") is None, "no user → skip"
    assert ps.get_profile("nobody-at-all") == {}, "unknown user → empty, not a crash"


def test_student_can_correct_what_ace_inferred():
    _seed()
    p = ps.set_profile(USER, interests=["rock climbing"], career_goals=[])
    assert p["interests"] == ["rock climbing"], "replaces rather than appends"
    assert p["career_goals"] == []
    assert ps.get_profile(USER)["interests"] == ["rock climbing"]


def test_snippet_is_empty_until_something_is_known():
    _seed()
    ps.set_profile(USER, interests=[], career_goals=[])
    assert ps.build_profile_snippet(USER) == "", "no profile → no prompt block"

    ps.set_profile(USER, interests=["dancing"], career_goals=["machine learning"])
    snippet = ps.build_profile_snippet(USER)
    assert "dancing" in snippet and "machine learning" in snippet
    assert "never let it override" in snippet, "must warn against hijacking the question"


def test_caps_hold():
    _seed()
    ps.set_profile(USER, interests=[f"interest {i}" for i in range(40)])
    assert len(ps.get_profile(USER)["interests"]) == ps.MAX_INTERESTS


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall profile checks passed")
