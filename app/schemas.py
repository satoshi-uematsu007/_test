from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


class UserCreate(BaseModel):
    email: EmailStr


class UserRead(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime

    class Config:
        orm_mode = True


class SessionBase(BaseModel):
    memo: Optional[str] = None


class SessionStart(SessionBase):
    started_at: Optional[datetime] = Field(default=None, description="Timezone-aware datetime")

    @validator("started_at")
    def validate_timezone(cls, value: Optional[datetime]):
        if value is not None and value.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        return value


class SessionStop(BaseModel):
    ended_at: Optional[datetime] = Field(default=None, description="Timezone-aware datetime")

    @validator("ended_at")
    def validate_timezone(cls, value: Optional[datetime]):
        if value is not None and value.tzinfo is None:
            raise ValueError("ended_at must be timezone-aware")
        return value


class SessionRead(BaseModel):
    id: int
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    memo: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


class DailySessionSummary(BaseModel):
    session_id: int
    minutes: int
    started_at: datetime
    ended_at: Optional[datetime]


class DailyStats(BaseModel):
    date: date
    total_minutes: int
    sessions: List[DailySessionSummary]


class WeeklyDaySummary(BaseModel):
    date: date
    minutes: int


class WeeklyStats(BaseModel):
    week_start: date
    week_end: date
    total_minutes: int
    by_day: List[WeeklyDaySummary]
