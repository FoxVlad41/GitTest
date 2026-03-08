from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Discount(SQLModel, table=True):
    """Модель для хранения скидок на временные слоты"""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Дата и слот, на который действует скидка
    date: str = Field(index=True)  # формат ДД.ММ.ГГГГ
    time_slot: str                  # например "13:00-15:00"
    machine_number: Optional[int] = Field(default=None)  # None = все машины
    
    # Параметры скидки
    discount_percent: int = Field(default=0)  # 0-100
    is_active: bool = Field(default=True)
    
    # Для отслеживания
    predicted_load: Optional[float] = Field(default=None)  # прогнозируемая загрузка %
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "15.03.2025",
                "time_slot": "09:00-11:00",
                "machine_number": None,
                "discount_percent": 30,
                "predicted_load": 25.5
            }
        }


class DiscountUpdate(SQLModel):
    """Модель для обновления скидки"""
    discount_percent: int
    is_active: Optional[bool] = True
    machine_number: Optional[int] = None


class DiscountResponse(SQLModel):
    """Модель для ответа со скидкой"""
    id: int
    date: str
    time_slot: str
    machine_number: Optional[int]
    discount_percent: int
    is_active: bool
    predicted_load: Optional[float]