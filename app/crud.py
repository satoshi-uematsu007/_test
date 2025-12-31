from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models


class ConflictError(Exception):
    """Raised when a business constraint is violated."""


class NotFoundError(Exception):
    """Raised when an entity cannot be located."""


class ValidationError(Exception):
    """Raised when input data is invalid."""


# User operations

def create_user(db: Session, email: str) -> models.User:
    user = models.User(email=email)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValidationError("Email already exists") from exc
    db.refresh(user)
    return user


def get_user(db: Session, user_id) -> models.User:
    user = db.get(models.User, user_id)
    if not user:
        raise NotFoundError("User not found")
    return user


# Session operations

def _ensure_no_active_session(db: Session, user_id) -> None:
    active_exists = db.execute(
        select(func.count(models.StudySession.id)).where(
            models.StudySession.user_id == user_id, models.StudySession.ended_at.is_(None)
        )
    ).scalar_one()
    if active_exists:
        raise ConflictError("Active session already exists")


def start_session(
    db: Session, *, user_id, started_at: Optional[datetime] = None, memo: Optional[str] = None
) -> models.StudySession:
    get_user(db, user_id)  # ensure exists
    _ensure_no_active_session(db, user_id)
    started_at = started_at or datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        raise ValidationError("started_at must be timezone-aware")

    session = models.StudySession(user_id=user_id, started_at=started_at, memo=memo)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def stop_session(db: Session, *, user_id, session_id, ended_at: Optional[datetime] = None) -> models.StudySession:
    session = db.get(models.StudySession, session_id)
    if not session or str(session.user_id) != str(user_id):
        raise NotFoundError("Session not found")
    if session.ended_at is not None:
        raise ConflictError("Session already stopped")

    ended_at = ended_at or datetime.now(timezone.utc)
    if ended_at.tzinfo is None:
        raise ValidationError("ended_at must be timezone-aware")
    if ended_at <= session.started_at:
        raise ValidationError("ended_at must be after started_at")

    session.ended_at = ended_at
    db.commit()
    db.refresh(session)
    return session


def list_sessions(
    db: Session,
    *,
    user_id,
    start_from: Optional[datetime] = None,
    start_to: Optional[datetime] = None,
    status: str = "all",
) -> List[models.StudySession]:
    get_user(db, user_id)
    query = select(models.StudySession).where(models.StudySession.user_id == user_id)

    if status == "active":
        query = query.where(models.StudySession.ended_at.is_(None))
    elif status == "closed":
        query = query.where(models.StudySession.ended_at.is_not(None))

    if start_from:
        query = query.where(models.StudySession.started_at >= start_from)
    if start_to:
        query = query.where(models.StudySession.started_at <= start_to)

    query = query.order_by(models.StudySession.started_at.desc())
    return db.execute(query).scalars().all()


def delete_session(db: Session, *, user_id, session_id) -> None:
    session = db.get(models.StudySession, session_id)
    if not session or str(session.user_id) != str(user_id):
        raise NotFoundError("Session not found")
    db.delete(session)
    db.commit()


# Stats helpers

def _overlap_minutes(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> int:
    latest_start = max(start, window_start)
    earliest_end = min(end, window_end)
    if latest_start >= earliest_end:
        return 0
    return int((earliest_end - latest_start).total_seconds() // 60)


def daily_stats(db: Session, *, user_id, target_date: date):
    get_user(db, user_id)
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

    query = select(models.StudySession).where(
        and_(
            models.StudySession.user_id == user_id,
            models.StudySession.ended_at.is_not(None),
            models.StudySession.started_at < day_end,
            models.StudySession.ended_at > day_start,
        )
    )
    sessions = db.execute(query).scalars().all()

    session_summaries = []
    total_minutes = 0
    for session in sessions:
        minutes = _overlap_minutes(session.started_at, session.ended_at, day_start, day_end)
        total_minutes += minutes
        session_summaries.append(
            {
                "session_id": session.id,
                "minutes": minutes,
                "started_at": session.started_at,
                "ended_at": session.ended_at,
            }
        )

    return {
        "date": target_date,
        "total_minutes": total_minutes,
        "sessions": session_summaries,
    }


def weekly_stats(db: Session, *, user_id, week_start: date):
    get_user(db, user_id)
    week_start_dt = datetime.combine(week_start, time.min, tzinfo=timezone.utc)
    week_end_dt = week_start_dt + timedelta(days=7) - timedelta(microseconds=1)

    query = select(models.StudySession).where(
        and_(
            models.StudySession.user_id == user_id,
            models.StudySession.ended_at.is_not(None),
            models.StudySession.started_at < week_end_dt,
            models.StudySession.ended_at > week_start_dt,
        )
    )
    sessions = db.execute(query).scalars().all()

    by_day = []
    total_minutes = 0
    for offset in range(7):
        current_date = week_start + timedelta(days=offset)
        window_start = datetime.combine(current_date, time.min, tzinfo=timezone.utc)
        window_end = datetime.combine(current_date, time.max, tzinfo=timezone.utc)
        minutes = sum(
            _overlap_minutes(s.started_at, s.ended_at, window_start, window_end)
            for s in sessions
        )
        total_minutes += minutes
        by_day.append({"date": current_date, "minutes": minutes})

    return {
        "week_start": week_start,
        "week_end": week_start + timedelta(days=6),
        "total_minutes": total_minutes,
        "by_day": by_day,
    }
