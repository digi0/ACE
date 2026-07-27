"""Self-check for major classification + record selection.

Run: python -m backend.test_routing
"""
from backend.services.chat_service import classify_major, select_top_records


def test_classify_major():
    # The CMPSC handbook documents the UP Engineering program — it must route to RAG.
    assert classify_major("Computer Science, B.S. (Engineering)") == "cs"
    assert classify_major("Computer Science, B.S. (Abington)") == "cs"
    assert classify_major("Data Sciences, B.S. (Science)") == "ds"
    assert classify_major("Psychology, B.A. (Liberal Arts)") == "other"
    assert classify_major(None) is None


def test_select_top_records():
    records = (
        [{"source_type": "pdf_handbook", "id": i} for i in range(6)]
        + [{"source_type": "web_bulletin", "id": i} for i in range(6)]
        + [{"source_type": "excel_vault", "id": i} for i in range(6)]  # retired source
    )
    for intent in ["courses", "student_progress", "substitution", "transfer",
                   "etm", "contact", "gen_ed", "deadline", "general"]:
        picked = select_top_records(records, intent)
        assert picked, f"{intent} selected no records"
        assert all(r["source_type"] != "excel_vault" for r in picked), \
            f"{intent} still selects retired excel_vault records"


if __name__ == "__main__":
    test_classify_major()
    test_select_top_records()
    print("routing self-check OK")
