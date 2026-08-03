"""Persist chat exchanges so the launch is measurable.

The `conversations` / `messages` tables existed since the schema was written but
nothing ever wrote to them — chat history lived only in the browser's localStorage.
That made three questions unanswerable: which *categories* of question students ask
(the north-star metric), which answers they rate badly, and which answers landed
ungrounded. This module is what fills them in.

Persistence is always best-effort: a DB failure must never break a student's answer,
so every write is wrapped and logged rather than raised.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from backend.database import SessionLocal
from backend.models import Conversation, Message

logger = logging.getLogger(__name__)


def save_exchange(user_id, conversation_id, question, answer, intent, sources):
    """Write the user question and the assistant answer as two rows.

    Returns the assistant Message id so the client can rate it, or None if the
    write failed or was skipped. Never raises.
    """
    if not user_id or not conversation_id or not answer:
        return None

    db = SessionLocal()
    try:
        # The conversation row may not exist yet — the id is minted client-side.
        if not db.get(Conversation, conversation_id):
            db.add(Conversation(
                id=conversation_id,
                user_id=user_id,
                title=question[:200] or None,
            ))

        db.add(Message(
            conversation_id=conversation_id,
            role="user",
            content=question,
        ))
        assistant = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            intent=intent,
            sources_json=json.dumps(sources or []),
        )
        db.add(assistant)
        db.commit()
        return assistant.id
    except Exception as e:
        db.rollback()
        # Deliberately swallowed: the student already has their answer on screen.
        logger.error("save_exchange | failed to persist: %s", e, exc_info=True)
        return None
    finally:
        db.close()


def set_rating(db, message_id, rating, user_id):
    """Record a thumbs rating. Returns True if it landed.

    Scoped to the calling user's own conversations so one student cannot rate
    another's answers.
    """
    msg = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Message.id == message_id, Conversation.user_id == user_id)
        .first()
    )
    if not msg or msg.role != "assistant":
        return False
    msg.rating = rating
    db.commit()
    return True


def review_summary(db, days=7):
    """The weekly review: what students asked, and where ACE fell short.

    Ungrounded answers (no sources) are the closest proxy available for the
    playbook's "dead end" — an answer given without anything backing it.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    answers = (
        db.query(Message)
        .filter(Message.role == "assistant", Message.created_at >= since)
    )

    by_intent = dict(
        db.query(Message.intent, func.count(Message.id))
        .filter(Message.role == "assistant", Message.created_at >= since)
        .group_by(Message.intent)
        .all()
    )

    total = answers.count()
    down = answers.filter(Message.rating == -1).all()
    ungrounded = answers.filter(
        (Message.sources_json == "[]") | (Message.sources_json.is_(None))
    ).all()

    return {
        "window_days": days,
        "answers": total,
        # The north-star input: distinct categories asked, and the spread.
        "categories_asked": len([k for k in by_intent if k]),
        "by_intent": by_intent,
        "rated_up": answers.filter(Message.rating == 1).count(),
        "rated_down": len(down),
        "unrated": answers.filter(Message.rating.is_(None)).count(),
        "ungrounded": len(ungrounded),
        # The two lists worth reading by hand every week.
        "down_rated_questions": [_question_for(db, m) for m in down[:50]],
        "ungrounded_questions": [_question_for(db, m) for m in ungrounded[:50]],
    }


def _question_for(db, assistant_msg):
    """The user question immediately preceding an assistant answer."""
    q = (
        db.query(Message)
        .filter(
            Message.conversation_id == assistant_msg.conversation_id,
            Message.role == "user",
            Message.id < assistant_msg.id,
        )
        .order_by(Message.id.desc())
        .first()
    )
    return {
        "question": q.content if q else None,
        "intent": assistant_msg.intent,
        "created_at": assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
    }
