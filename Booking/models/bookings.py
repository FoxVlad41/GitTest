from pydantic import BaseModel
from datetime import date

#Модель для хранения брони
class Booking(BaseModel):
    id: int
    user_id: int
    date: str
    time_slot: str  #Временной слот (например: "9:00-11:00")
    #Пример модели
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "date": "01.01.2025",
                "time_slot": "9:00-11:00"
            }
        }
#Модель для создания брони
class BookingCreate(BaseModel):
    user_id: int
    date: str
    time_slot: str