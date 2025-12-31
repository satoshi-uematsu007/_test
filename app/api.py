from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from . import crud, schemas
from .db import get_db

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/users", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_user(db, email=user.email)
    except crud.ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/users/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: str, db: Session = Depends(get_db)):
    try:
        return crud.get_user(db, user_id)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/users/{user_id}/sessions/start",
    response_model=schemas.SessionRead,
    status_code=status.HTTP_201_CREATED,
)
def start_session(
    user_id: str,
    payload: schemas.SessionStart,
    db: Session = Depends(get_db),
):
    try:
        return crud.start_session(db, user_id=user_id, started_at=payload.started_at, memo=payload.memo)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except crud.ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except crud.ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/users/{user_id}/sessions/{session_id}/stop",
    response_model=schemas.SessionRead,
)
def stop_session(user_id: str, session_id: int, payload: schemas.SessionStop, db: Session = Depends(get_db)):
    try:
        return crud.stop_session(db, user_id=user_id, session_id=session_id, ended_at=payload.ended_at)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except crud.ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except crud.ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/users/{user_id}/sessions", response_model=list[schemas.SessionRead])
def list_sessions(
    user_id: str,
    from_param: Optional[datetime] = Query(None, alias="from"),
    to_param: Optional[datetime] = Query(None, alias="to"),
    status_param: str = Query("all", regex="^(active|closed|all)$"),
    db: Session = Depends(get_db),
):
    try:
        return crud.list_sessions(
            db,
            user_id=user_id,
            start_from=from_param,
            start_to=to_param,
            status=status_param,
        )
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/users/{user_id}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(user_id: str, session_id: int, db: Session = Depends(get_db)):
    try:
        crud.delete_session(db, user_id=user_id, session_id=session_id)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/users/{user_id}/stats/daily", response_model=schemas.DailyStats)
def daily_stats(user_id: str, date_param: Optional[date] = Query(None, alias="date"), db: Session = Depends(get_db)):
    target_date = date_param or date.today()
    try:
        data = crud.daily_stats(db, user_id=user_id, target_date=target_date)
        return data
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/users/{user_id}/stats/weekly", response_model=schemas.WeeklyStats)
def weekly_stats(user_id: str, week_start: Optional[date] = Query(None), db: Session = Depends(get_db)):
    start_date = week_start or date.today()
    # Align to week start (Monday) if not provided
    start_date = start_date - timedelta(days=start_date.weekday()) if week_start is None else start_date
    try:
        data = crud.weekly_stats(db, user_id=user_id, week_start=start_date)
        return data
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
