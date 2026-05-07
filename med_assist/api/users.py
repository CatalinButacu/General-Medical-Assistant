"""User-scoped endpoints. user_id is taken from the verified JWT, never from the request body."""

from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from med_assist.auth import current_user_sub
from med_assist.db import CabinetItem, HealthProfile, get_session

router = APIRouter(prefix="/user", tags=["user"])


# ───────────────── profile ─────────────────


class ProfileIn(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[str] = Field(default=None, pattern="^(male|female|other)$")
    isPregnant: Optional[bool] = None
    pregnancyDueDate: Optional[date] = None
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    onboarded: Optional[bool] = None


class ProfileOut(ProfileIn):
    user_id: str


def _profile_to_dto(p: HealthProfile) -> ProfileOut:
    return ProfileOut(
        user_id=p.user_id,
        name=p.name,
        age=p.age,
        gender=p.gender,
        isPregnant=p.is_pregnant,
        pregnancyDueDate=p.pregnancy_due_date,
        allergies=list(p.allergies or []),
        conditions=list(p.conditions or []),
        medications=list(p.medications or []),
        onboarded=p.onboarded,
    )


@router.get("/profile", response_model=ProfileOut)
def get_profile(sub: str = Depends(current_user_sub), db: Session = Depends(get_session)):
    p = db.get(HealthProfile, sub)
    if not p:
        return ProfileOut(user_id=sub)
    return _profile_to_dto(p)


@router.put("/profile", response_model=ProfileOut)
def upsert_profile(
    body: ProfileIn,
    sub: str = Depends(current_user_sub),
    db: Session = Depends(get_session),
):
    p = db.get(HealthProfile, sub)
    if p is None:
        p = HealthProfile(user_id=sub)
        db.add(p)
    p.name = body.name
    p.age = body.age
    p.gender = body.gender
    p.is_pregnant = bool(body.isPregnant)
    p.pregnancy_due_date = body.pregnancyDueDate
    p.allergies = body.allergies
    p.conditions = body.conditions
    p.medications = body.medications
    if body.onboarded is not None:
        p.onboarded = body.onboarded
    db.commit()
    db.refresh(p)
    return _profile_to_dto(p)


# ───────────────── cabinet ─────────────────


class CabinetItemIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    generic_name: Optional[str] = Field(None, max_length=200)
    dosage: Optional[str] = Field(None, max_length=100)
    item_type: Optional[str] = Field(None, max_length=50)
    quantity: int = Field(1, ge=1)
    expiration_date: date
    notes: Optional[str] = Field(None, max_length=1000)


class CabinetItemOut(CabinetItemIn):
    id: UUID
    added_date: date


def _cabinet_to_dto(c: CabinetItem) -> CabinetItemOut:
    return CabinetItemOut(
        id=c.id,
        name=c.name,
        generic_name=c.generic_name,
        dosage=c.dosage,
        item_type=c.item_type,
        quantity=c.quantity,
        expiration_date=c.expiration_date,
        added_date=c.added_date,
        notes=c.notes,
    )


@router.get("/cabinet", response_model=list[CabinetItemOut])
def list_cabinet(sub: str = Depends(current_user_sub), db: Session = Depends(get_session)):
    rows = db.execute(
        select(CabinetItem).where(CabinetItem.user_id == sub).order_by(CabinetItem.expiration_date)
    ).scalars().all()
    return [_cabinet_to_dto(r) for r in rows]


@router.post("/cabinet", response_model=CabinetItemOut, status_code=201)
def add_cabinet_item(
    body: CabinetItemIn,
    sub: str = Depends(current_user_sub),
    db: Session = Depends(get_session),
):
    item = CabinetItem(
        user_id=sub,
        name=body.name,
        generic_name=body.generic_name,
        dosage=body.dosage,
        item_type=body.item_type,
        quantity=body.quantity,
        expiration_date=body.expiration_date,
        notes=body.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _cabinet_to_dto(item)


@router.put("/cabinet/{item_id}", response_model=CabinetItemOut)
def update_cabinet_item(
    item_id: UUID,
    body: CabinetItemIn,
    sub: str = Depends(current_user_sub),
    db: Session = Depends(get_session),
):
    item = db.get(CabinetItem, item_id)
    if item is None or item.user_id != sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found.")
    item.name = body.name
    item.generic_name = body.generic_name
    item.dosage = body.dosage
    item.item_type = body.item_type
    item.quantity = body.quantity
    item.expiration_date = body.expiration_date
    item.notes = body.notes
    db.commit()
    db.refresh(item)
    return _cabinet_to_dto(item)


@router.delete("/cabinet/{item_id}", status_code=204)
def delete_cabinet_item(
    item_id: UUID,
    sub: str = Depends(current_user_sub),
    db: Session = Depends(get_session),
):
    item = db.get(CabinetItem, item_id)
    if item is None or item.user_id != sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found.")
    db.delete(item)
    db.commit()
    return None
