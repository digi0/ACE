"""Self-check for the waitlist invite flow.

Ten people raised their hand and none of them could get in — `invited_at` existed
on the model and nothing ever set it. This covers the motion that fixes that, and
the two properties that matter once real invites are out in the world: running it
twice must not invalidate a code somebody is holding, and redeeming one must be
recorded, because "invited" and "actually came in" are different numbers and only
the second one means anything.

    python -m backend.test_invite
"""

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='.db')}"
os.environ["ADMIN_KEY"] = "test-admin"
os.environ["ACCESS_CODE"] = "shared-pilot"

import backend.main as m  # noqa: E402 — env must be set before the engine is built
from backend import models  # noqa: E402
from backend.database import SessionLocal  # noqa: E402
from backend.main import AccessRequest  # noqa: E402

KEY = "test-admin"


def _fresh_db(n=3):
    db = SessionLocal()
    db.query(models.WaitlistEntry).delete()
    db.commit()
    for i in range(n):
        db.add(models.WaitlistEntry(email=f"s{i}@psu.edu", major="Computer Science"))
    db.commit()
    return db


def test_invites_go_out_oldest_first_and_stop_at_the_limit():
    db = _fresh_db(3)
    out = m.admin_waitlist_invite(limit=2, key=KEY, x_admin_key=None, db=db)
    assert out["invited_now"] == 2
    assert out["still_waiting"] == 1
    assert all(i["code"].startswith("ACE-") for i in out["invites"])
    assert len({i["code"] for i in out["invites"]}) == 2, "codes must be unique"
    db.close()


def test_running_it_twice_does_not_invalidate_a_code_someone_holds():
    db = _fresh_db(3)
    first = m.admin_waitlist_invite(limit=2, key=KEY, x_admin_key=None, db=db)
    held = first["invites"][0]["code"]
    m.admin_waitlist_invite(limit=5, key=KEY, x_admin_key=None, db=db)
    row = db.query(models.WaitlistEntry).filter_by(email="s0@psu.edu").first()
    assert row.access_code == held, "a re-run must not re-mint a live invite"
    db.close()


def test_a_personal_code_opens_the_gate_and_records_that_it_did():
    db = _fresh_db(2)
    out = m.admin_waitlist_invite(limit=1, key=KEY, x_admin_key=None, db=db)
    code = out["invites"][0]["code"]

    assert m.verify_access(AccessRequest(code=code), db) == {"ok": True}
    row = db.query(models.WaitlistEntry).filter_by(access_code=code).first()
    assert row.redeemed_at is not None, "redemption is the only signal of conversion"

    first_seen = row.redeemed_at
    m.verify_access(AccessRequest(code=code), db)
    db.refresh(row)
    assert row.redeemed_at == first_seen, "re-entering must not restamp first entry"
    db.close()


def test_the_shared_code_still_works_and_a_wrong_one_does_not():
    db = _fresh_db(1)
    assert m.verify_access(AccessRequest(code="shared-pilot"), db) == {"ok": True}
    # An empty code never reaches the handler — AccessRequest's min_length turns
    # it into a 422 first — so the cases worth asserting here are the ones that
    # DO get through: whitespace, a near-miss, and a well-formed wrong code.
    for bad in ["ACE-ZZZZZZ", "   ", "shared-pilotx"]:
        try:
            m.verify_access(AccessRequest(code=bad), db)
            raise AssertionError(f"{bad!r} should not open the gate")
        except Exception as e:
            assert getattr(e, "status_code", None) == 403, f"{bad!r} → {e}"
    db.close()


def test_codes_avoid_characters_people_misread():
    db = _fresh_db(6)
    out = m.admin_waitlist_invite(limit=6, key=KEY, x_admin_key=None, db=db)
    body = "".join(i["code"].removeprefix("ACE-") for i in out["invites"])
    for c in "O0I1S5":
        assert c not in body, f"{c!r} is misread off a phone screen"
    db.close()


def test_the_admin_view_reports_conversion_not_just_invitations():
    db = _fresh_db(3)
    out = m.admin_waitlist_invite(limit=3, key=KEY, x_admin_key=None, db=db)
    m.verify_access(AccessRequest(code=out["invites"][0]["code"]), db)
    summary = m.admin_waitlist(key=KEY, x_admin_key=None, db=db)
    assert summary["invited"] == 3 and summary["redeemed"] == 1
    db.close()


def test_it_never_sends_anything_itself():
    """Delivering an invite is a person's decision. The endpoint hands back the
    addresses and the copy; nothing in this path talks to a mail server."""
    db = _fresh_db(1)
    out = m.admin_waitlist_invite(limit=1, key=KEY, x_admin_key=None, db=db)
    assert "message_template" in out and "{code}" in out["message_template"]
    src = open("backend/main.py", encoding="utf-8").read()
    for smtp in ("smtplib", "sendgrid", "mailgun", "ses.send_email", "postmark"):
        assert smtp not in src, f"{smtp} would mean ACE emails students on its own"
    db.close()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("\nall invite checks passed")
