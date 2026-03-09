from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import bookings, events, auth
from src.database import init_db


app = FastAPI(
    title="Book Ticketing API",
    description="API for booking tickets to shows, concerts, and events",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://booktickets.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "book-ticketing-api"}
