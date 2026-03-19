from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd

from models.analytics import AnalyticsData
from database.connection import get_session

analytics_crud_router = APIRouter(
    prefix="/analytics-data",
    tags=["Analytics Data CRUD"]
)


# ================ CREATE ================

@analytics_crud_router.post("/", response_model=dict)
async def create_analytics_entry(
        entry: AnalyticsData,
        session: Session = Depends(get_session)
) -> dict:
    """
    Создать новую запись в аналитической таблице
    """
    try:
        session.add(entry)
        session.commit()
        session.refresh(entry)

        return {
            "message": "Запись успешно создана",
            "entry": {
                "id": entry.id,
                "booking_date": entry.booking_date,
                "time_slot": entry.booking_time_slot,
                "was_booked": entry.was_booked
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании записи: {str(e)}"
        )


# ================ READ ================

@analytics_crud_router.get("/", response_model=dict)
async def get_all_analytics(
        skip: int = Query(0, description="Сколько записей пропустить"),
        limit: int = Query(100, description="Сколько записей вернуть"),
        session: Session = Depends(get_session)
) -> dict:
    """
    Получить все записи из аналитической таблицы
    """
    try:
        # Получаем общее количество записей
        total = session.exec(select(func.count(AnalyticsData.id))).one()

        # Получаем записи с пагинацией
        query = select(AnalyticsData).offset(skip).limit(limit)
        entries = session.exec(query).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "entries": [
                {
                    "id": e.id,
                    "booking_id": e.booking_id,
                    "booking_date": e.booking_date,
                    "booking_time_slot": e.booking_time_slot,
                    "booking_machine_number": e.booking_machine_number,
                    "user_id": e.user_id,
                    "user_fio": e.user_fio,
                    "day_of_week": e.day_of_week,
                    "hour_start": e.hour_start,
                    "month": e.month,
                    "year": e.year,
                    "is_weekend": e.is_weekend,
                    "slot_datetime": e.slot_datetime.isoformat() if e.slot_datetime else None,
                    "was_booked": e.was_booked,
                    "created_at": e.created_at.isoformat() if e.created_at else None
                }
                for e in entries
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении записей: {str(e)}"
        )


@analytics_crud_router.get("/{entry_id}", response_model=dict)
async def get_analytics_entry(
        entry_id: int,
        session: Session = Depends(get_session)
) -> dict:
    """
    Получить конкретную запись по ID
    """
    entry = session.get(AnalyticsData, entry_id)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Запись с ID {entry_id} не найдена"
        )

    return {
        "id": entry.id,
        "booking_id": entry.booking_id,
        "booking_date": entry.booking_date,
        "booking_time_slot": entry.booking_time_slot,
        "booking_machine_number": entry.booking_machine_number,
        "booking_created_at": entry.booking_created_at.isoformat() if entry.booking_created_at else None,
        "user_id": entry.user_id,
        "user_fio": entry.user_fio,
        "user_phone": entry.user_phone,
        "day_of_week": entry.day_of_week,
        "hour_start": entry.hour_start,
        "month": entry.month,
        "year": entry.year,
        "is_weekend": entry.is_weekend,
        "slot_datetime": entry.slot_datetime.isoformat() if entry.slot_datetime else None,
        "was_booked": entry.was_booked,
        "created_at": entry.created_at.isoformat() if entry.created_at else None
    }

# ================ UPDATE ================

@analytics_crud_router.put("/{entry_id}", response_model=dict)
async def update_analytics_entry(
        entry_id: int,
        entry_update: dict,
        session: Session = Depends(get_session)
) -> dict:
    """
    Обновить существующую запись
    """
    entry = session.get(AnalyticsData, entry_id)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Запись с ID {entry_id} не найдена"
        )

    try:
        # Обновляем только переданные поля
        for key, value in entry_update.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        session.add(entry)
        session.commit()
        session.refresh(entry)

        return {
            "message": "Запись успешно обновлена",
            "entry": {
                "id": entry.id,
                "booking_date": entry.booking_date,
                "time_slot": entry.booking_time_slot,
                "was_booked": entry.was_booked
            }
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении: {str(e)}"
        )
# ================ DELETE ================

@analytics_crud_router.delete("/{entry_id}", response_model=dict)
async def delete_analytics_entry(
        entry_id: int,
        session: Session = Depends(get_session)
) -> dict:
    """
    Удалить конкретную запись
    """
    entry = session.get(AnalyticsData, entry_id)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Запись с ID {entry_id} не найдена"
        )

    try:
        session.delete(entry)
        session.commit()

        return {
            "message": "Запись успешно удалена",
            "deleted_id": entry_id
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении: {str(e)}"
        )