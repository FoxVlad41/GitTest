from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class AnalyticsData(SQLModel, table=True):
    """Денормализованная таблица для аналитики и прогнозирования"""

    id: Optional[int] = Field(default=None, primary_key=True)

    # Данные из Booking
    booking_id: Optional[int] = Field(default=None, index=True)
    booking_date: str
    booking_time_slot: str
    booking_machine_number: int
    booking_created_at: Optional[datetime] = None

    # Данные из User (если есть)
    user_id: Optional[int] = Field(default=None, index=True)
    user_fio: Optional[str] = None
    user_phone: Optional[str] = None

    # Производные признаки для анализа
    day_of_week: int  # 0-6, где 0 - понедельник
    hour_start: int  # начальный час слота (например, 9 для "09:00-11:00")
    month: int  # 1-12
    year: int  # год
    is_weekend: bool  # выходной ли день
    slot_datetime: datetime  # полная дата+время для Prophet

    # Признак наличия бронирования
    was_booked: bool = Field(default=False)

    # Временная метка создания записи в аналитике
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "booking_id": 1,
                "booking_date": "15.03.2025",
                "booking_time_slot": "18:00-20:00",
                "booking_machine_number": 2,
                "user_id": 1,
                "user_fio": "Иванов Иван",
                "day_of_week": 5,
                "hour_start": 18,
                "month": 3,
                "year": 2025,
                "is_weekend": True,
                "was_booked": True
            }
        }