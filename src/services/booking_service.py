import random
import string

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.models.booking import Booking, BookingStatus
from src.models.event import Event
from src.services.email_service import EmailService
from src.services.payment_service import PaymentService


class BookingService:
    def __init__(self, db: Session):
        self.db = db

    def _generate_reference(self) -> str:
        chars = string.ascii_uppercase + string.digits
        return "".join(random.choices(chars, k=10))

    async def create_booking(self, user_id: int, event_id: int, seats: int) -> Booking:
        event = (
            self.db.query(Event).filter(Event.id == event_id).with_for_update().first()
        )

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        if event.available_seats < seats:
            raise HTTPException(status_code=400, detail="Not enough seats available")
        if seats < 1 or seats > 10:
            raise HTTPException(
                status_code=400, detail="You can book between 1 and 10 seats"
            )

        total_price = event.price * seats

        payment = await PaymentService.charge(user_id, total_price)
        if not payment.success:
            raise HTTPException(status_code=402, detail="Payment failed")

        booking = Booking(
            user_id=user_id,
            event_id=event_id,
            seats=seats,
            total_price=total_price,
            status=BookingStatus.CONFIRMED,
            reference=self._generate_reference(),
        )

        event.available_seats -= seats
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)

        await EmailService.send_confirmation(booking)

        return booking

    def get_by_reference(self, reference: str) -> Booking:
        return self.db.query(Booking).filter(Booking.reference == reference).first()

    async def cancel_booking(self, reference: str, user_id: int):
        booking = self.get_by_reference(reference)
        if not booking or booking.user_id != user_id:
            raise HTTPException(status_code=404, detail="Booking not found")
        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Booking already cancelled")

        booking.status = BookingStatus.CANCELLED
        event = self.db.query(Event).filter(Event.id == booking.event_id).first()
        event.available_seats += booking.seats

        self.db.commit()
        await EmailService.send_cancellation(booking)
