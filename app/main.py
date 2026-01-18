from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

app = FastAPI(title="Example Hotel")

ROOMS = [
    {
        "id": "room-101",
        "room_type": "queen",
        "price": 129,
        "features": ["wifi", "breakfast"],
    },
    {
        "id": "room-202",
        "room_type": "king",
        "price": 159,
        "features": ["wifi", "ocean_view"],
    },
    {
        "id": "room-303",
        "room_type": "suite",
        "price": 219,
        "features": ["wifi", "breakfast", "balcony"],
    },
]

BOOKINGS: Dict[str, "Booking"] = {}


class Room(BaseModel):
    id: str
    room_type: str
    price: int
    features: List[str]


class BookingRequest(BaseModel):
    room_id: str = Field(..., description="Room identifier")
    check_in: str = Field(..., description="YYYY-MM-DD")
    check_out: str = Field(..., description="YYYY-MM-DD")
    guest_name: str


class Booking(BaseModel):
    id: str
    room_id: str
    check_in: str
    check_out: str
    guest_name: str
    status: str


@app.get("/")
def root() -> Dict[str, str]:
    return {"service": "Example Hotel", "uap": "/.well-known/uap"}


@app.get("/.well-known/uap")
def uap_root(request: Request) -> Dict[str, object]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "name": "Example Hotel",
        "modules": [
            {
                "id": "booking",
                "description": "Room availability and booking",
                "href": f"{base_url}/.well-known/booking.json",
            }
        ],
    }


@app.get("/.well-known/booking.json")
def booking_module(request: Request) -> Dict[str, object]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "name": "Booking",
        "openapi": f"{base_url}/openapi.json",
        "actions": [
            {
                "id": "rooms.list",
                "description": "List all rooms",
                "method": "GET",
                "href": f"{base_url}/rooms",
            },
            {
                "id": "rooms.search",
                "description": "Search available rooms",
                "method": "GET",
                "href": f"{base_url}/rooms/search",
            },
            {
                "id": "booking.create",
                "description": "Create a booking",
                "method": "POST",
                "href": f"{base_url}/bookings",
                "confirm": "user",
            },
            {
                "id": "booking.cancel",
                "description": "Cancel a booking",
                "method": "POST",
                "href": f"{base_url}/bookings/{{booking_id}}/cancel",
                "confirm": "user",
            },
        ],
    }


@app.get("/rooms/search", response_model=List[Room])
def search_rooms(
    check_in: Optional[str] = Query(None, description="YYYY-MM-DD"),
    check_out: Optional[str] = Query(None, description="YYYY-MM-DD"),
    guests: Optional[int] = Query(None, ge=1),
) -> List[Room]:
    return [Room(**room) for room in ROOMS]


@app.get("/rooms", response_model=List[Room])
def list_rooms() -> List[Room]:
    return [Room(**room) for room in ROOMS]


@app.post("/bookings", response_model=Booking)
def create_booking(payload: BookingRequest) -> Booking:
    room = next((room for room in ROOMS if room["id"] == payload.room_id), None)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    booking_id = str(uuid.uuid4())
    booking = Booking(
        id=booking_id,
        room_id=payload.room_id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guest_name=payload.guest_name,
        status="confirmed",
    )
    BOOKINGS[booking_id] = booking
    return booking


@app.post("/bookings/{booking_id}/cancel", response_model=Booking)
def cancel_booking(booking_id: str) -> Booking:
    booking = BOOKINGS.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    updated = booking.copy(update={"status": "canceled"})
    BOOKINGS[booking_id] = updated
    return updated
