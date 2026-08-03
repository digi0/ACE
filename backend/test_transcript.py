"""Self-check for transcript persistence, rating, and the weekly review.

Runs against a throwaway SQLite file — never touches the real DB.

    python -m backend.test_transcript
"""

import json
import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.mkdtemp(), "test_transcript.db"
)

from backend.database import engine, Base, SessionLocal  # noqa: E402
from backend.models import Conversation, Message, User  # noqa: E402
from backend.services import transcript_service as ts  # noqa: E402
from backend.eval import from_transcripts as ft  # noqa: E402

Base.metadata.create_all(bind=engine)

USER = "user_abc"
OTHER = "user_xyz"


def test_save_exchange_creates_conversation_and_two_rows():
    mid = ts.save_exchange(
        USER, "conv-1", "what am I missing to graduate?",
        "You need 12 credits.", "student_progress",
        [{"title": "Handbook", "link": "http://x"}],
    )
    assert mid is not None, "should return the assistant message id"

    db = SessionLocal()
    try:
        assert db.get(Conversation, "conv-1") is not None, "conversation auto-created"
        rows = db.query(Message).filter(Message.conversation_id == "conv-1").all()
        assert len(rows) == 2, f"expected user+assistant rows, got {len(rows)}"

        assistant = db.get(Message, mid)
        assert assistant.role == "assistant"
        assert assistant.intent == "student_progress", "intent must persist — it is the north-star input"
        assert json.loads(assistant.sources_json)[0]["title"] == "Handbook"
        assert assistant.rating is None, "starts unrated"
    finally:
        db.close()


def test_second_exchange_reuses_conversation():
    ts.save_exchange(USER, "conv-1", "when is add/drop?", "Jan 20.", "deadline", [])
    db = SessionLocal()
    try:
        convs = db.query(Conversation).filter(Conversation.id == "conv-1").count()
        assert convs == 1, "must not duplicate the conversation row"
        assert db.query(Message).filter(Message.conversation_id == "conv-1").count() == 4
    finally:
        db.close()


def test_skips_when_inputs_missing():
    assert ts.save_exchange(None, "c", "q", "a", "i", []) is None, "no user → skip"
    assert ts.save_exchange(USER, None, "q", "a", "i", []) is None, "no conversation → skip"
    assert ts.save_exchange(USER, "c", "q", "", "i", []) is None, "empty answer → skip"


def test_rating_roundtrip_and_ownership():
    mid = ts.save_exchange(USER, "conv-2", "prereqs for CMPSC 221?", "CMPSC 132.", "courses", [{"a": 1}])
    db = SessionLocal()
    try:
        assert ts.set_rating(db, mid, 1, USER) is True
        assert db.get(Message, mid).rating == 1

        # Another student must not be able to rate someone else's answer.
        assert ts.set_rating(db, mid, -1, OTHER) is False, "cross-user rating must be refused"
        assert db.get(Message, mid).rating == 1, "rating unchanged after refused write"

        # A user-role row is not rateable.
        user_row = (
            db.query(Message)
            .filter(Message.conversation_id == "conv-2", Message.role == "user")
            .first()
        )
        assert ts.set_rating(db, user_row.id, 1, USER) is False, "user rows are not rateable"

        assert ts.set_rating(db, 999999, 1, USER) is False, "missing id → False, not a crash"
    finally:
        db.close()


def test_review_summary_counts_and_dead_ends():
    # One answer with no sources at all — the dead-end proxy.
    ts.save_exchange(USER, "conv-3", "where do I print?", "Not sure.", "general", [])
    db = SessionLocal()
    try:
        bad = (
            db.query(Message)
            .filter(Message.conversation_id == "conv-3", Message.role == "assistant")
            .first()
        )
        ts.set_rating(db, bad.id, -1, USER)

        r = ts.review_summary(db, days=7)
        assert r["answers"] == 4, f"4 assistant rows so far, got {r['answers']}"
        assert r["rated_up"] == 1
        assert r["rated_down"] == 1
        assert r["ungrounded"] >= 1, "empty sources must count as ungrounded"

        # The metric that decides the ecosystem thesis.
        assert r["categories_asked"] == 4, f"4 distinct intents, got {r['categories_asked']}"
        assert r["by_intent"]["deadline"] == 1

        qs = [d["question"] for d in r["down_rated_questions"]]
        assert "where do I print?" in qs, "review must surface the question, not just the answer"
    finally:
        db.close()


def test_review_window_excludes_nothing_recent():
    db = SessionLocal()
    try:
        assert ts.review_summary(db, days=1)["answers"] == 4, "all rows are fresh"
    finally:
        db.close()


def test_harvest_picks_up_bad_answers_only():
    # The harvester needs a User row to read the major from; the exchanges above
    # were written without one.
    db = SessionLocal()
    try:
        db.add(User(id=USER, selected_major="Psychology, B.A. (Liberal Arts)"))
        db.commit()

        rows = ft.harvest(db, days=7, limit=25)
        questions = [r["question"] for r in rows]
        assert "where do I print?" in questions, "down-rated answer must be harvested"
        assert "prereqs for CMPSC 221?" not in questions, (
            "a grounded, up-rated answer is not a regression candidate"
        )
        assert all(r["major"] == "Psychology, B.A. (Liberal Arts)" for r in rows), (
            "each item carries the major it was asked under"
        )
        assert {r["reason"] for r in rows} <= {"rated_down", "ungrounded"}
    finally:
        db.close()


def test_make_item_dedupes_ids_and_guards_scope():
    ids = {"real-general"}
    row = {"question": "where do I print?", "major": "Psychology, B.A. (Liberal Arts)",
           "intent": "general", "reason": "rated_down"}
    item = ft.make_item(row, ids, ["names a specific lab or building"])
    assert item["id"] == "real-general-2", f"id must not collide, got {item['id']}"
    assert item["must_not"] == ["CMPSC", "DTSCE"], "non-CS major keeps the scope guard"
    assert item["_drafted"] is True, "drafted points must be flagged for human review"

    cs_row = dict(row, major="Computer Science, B.S. (Engineering)")
    assert ft.make_item(cs_row, ids, [])["must_not"] == [], "CS major must not forbid CMPSC"

    assert ft.normalize("Where do I PRINT?!") == ft.normalize("where do i print"), (
        "dedupe must survive case and punctuation"
    )


if __name__ == "__main__":
    # Definition order, not sorted — these build on a shared DB and the later
    # count assertions depend on the earlier writes having happened.
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall transcript checks passed")
