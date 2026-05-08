"""Authenticated chat-history endpoints. Persistence is opt-in: only authenticated
clients call these around /chat. /chat itself stays stateless and unauth."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from med_assist.auth import current_user_sub
from med_assist.db import ChatMessage, ChatSession, get_session

router = APIRouter(prefix="/user/chats", tags=["chats"])

_MAX_TITLE = 200
_MAX_MESSAGE = 4000


class SessionIn(BaseModel):
    title: Optional[str] = Field(None, max_length=_MAX_TITLE)


class SessionSummary(BaseModel):
    id: UUID
    title: Optional[str]
    message_count: int
    created_at: datetime
    updated_at: datetime


class MessageIn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    text: str = Field(..., min_length=1, max_length=_MAX_MESSAGE)


class MessageOut(MessageIn):
    id: UUID
    created_at: datetime


class SessionDetail(BaseModel):
    id: UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut]


def _own_session_or_404(db: Session, session_id: UUID, sub: str) -> ChatSession:
    s = db.get(ChatSession, session_id)
    if s is None or s.user_id != sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    return s


@router.post("", response_model=SessionSummary, status_code=201)
def create_session(
    body: SessionIn,
    sub: str = Depends(current_user_sub),
    db: Session = Depends(get_session),
):
    s = ChatSession(user_id=sub, title=body.title)
    db.add(s)
    db.commit()
    db.refresh(s)
    return SessionSummary(
        id=s.id, title=s.title, message_count=0,
        created_at=s.created_at, updated_at=s.updated_at,
    )


@router.get("", response_model=list[SessionSummary])
def list_sessions(sub: str = Depends(current_user_sub), db: Session = Depends(get_session)):
    msg_count = (
        select(ChatMessage.session_id, func.count(ChatMessage.id).label("c"))
        .group_by(ChatMessage.session_id)
        .subquery()
    )
    rows = db.execute(
        select(ChatSession, func.coalesce(msg_count.c.c, 0))
        .join(msg_count, msg_count.c.session_id == ChatSession.id, isouter=True)
        .where(ChatSession.user_id == sub)
        .order_by(ChatSession.updated_at.desc())
    ).all()
    return [
        SessionSummary(
            id=s.id, title=s.title, message_count=int(c),
            created_at=s.created_at, updated_at=s.updated_at,
        )
        for s, c in rows
    ]


@router.get("/{session_id}", response_model=SessionDetail)
def get_session_detail(
    session_id: UUID,
    sub: str = Depends(current_user_sub),
    db: Session = Depends(get_session),
):
    s = _own_session_or_404(db, session_id, sub)
    return SessionDetail(
        id=s.id, title=s.title,
        created_at=s.created_at, updated_at=s.updated_at,
        messages=[
            MessageOut(id=m.id, role=m.role, text=m.text, created_at=m.created_at)
            for m in s.messages
        ],
    )


@router.post("/{session_id}/messages", response_model=MessageOut, status_code=201)
def append_message(
    session_id: UUID,
    body: MessageIn,
    sub: str = Depends(current_user_sub),
    db: Session = Depends(get_session),
):
    s = _own_session_or_404(db, session_id, sub)
    msg = ChatMessage(session_id=s.id, role=body.role, text=body.text)
    db.add(msg)
    # Auto-title from the first user message so /user/chats listings are scannable.
    if s.title is None and body.role == "user":
        s.title = body.text[:80]
    db.commit()
    db.refresh(msg)
    return MessageOut(id=msg.id, role=msg.role, text=msg.text, created_at=msg.created_at)


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: UUID,
    sub: str = Depends(current_user_sub),
    db: Session = Depends(get_session),
):
    s = _own_session_or_404(db, session_id, sub)
    db.delete(s)
    db.commit()
    return None
