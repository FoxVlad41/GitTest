from sqlmodel import SQLModel, Field, JSON, Column
from typing import List, Optional
from datetime import datetime


class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    date: str = Field(index=True)  #формат - дд.мм.гггг
    time_slot: str  #"09:00-11:00"
    machine_number: int
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "date": "01.01.2025",
                "time_slot": "09:00-11:00",
                "machine_number": 1
            }
        }


class BookingCreate(SQLModel):
    user_id: int
    date: str
    time_slot: str
    machine_number: int


class BookingResponse(SQLModel):
    id: int
    user_id: int
    date: str
    time_slot: str
    machine_number: int


class StatisticsResponse(SQLModel):
    machine_usage: dict
    popular_slots: List[dict]
    #machine_slot_statistics: dict
    #total_bookings: int