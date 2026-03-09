from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.event import Event

router = APIRouter()


class EventResponse(BaseModel):
    id: int
    title: str
    venue: str
    event_date: datetime
    available_seats: int
    price: float


@router.get("/", response_model=List[EventResponse])
def list_events(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    skip: int = 0,
    limit: int = 20,
):
    query = db.query(Event).filter(Event.is_active)
    if search:
        query = query.filter(Event.title.ilike(f"%{search}%"))
    if min_price:
        query = query.filter(Event.price >= min_price)
    if max_price:
        query = query.filter(Event.price <= max_price)
    return query.offset(skip).limit(limit).all()


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Event not found")
    return event
