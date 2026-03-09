from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.booking_service import BookingService
from src.utils.auth import get_current_user

router = APIRouter()


class BookingRequest(BaseModel):
    event_id: int
    seats: int


class BookingResponse(BaseModel):
    id: int
    reference: str
    event_id: int
    seats: int
    total_price: float
    status: str


@router.post("/", response_model=BookingResponse, status_code=201)
async def create_booking(
    payload: BookingRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = BookingService(db)
    booking = await service.create_booking(
        user_id=current_user.id, event_id=payload.event_id, seats=payload.seats
    )
    return booking


@router.get("/{reference}", response_model=BookingResponse)
async def get_booking(
    reference: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = BookingService(db)
    booking = service.get_by_reference(reference)
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.delete("/{reference}", status_code=204)
async def cancel_booking(
    reference: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = BookingService(db)
    await service.cancel_booking(reference, current_user.id)
