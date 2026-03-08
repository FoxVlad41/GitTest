from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select, delete
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Optional

from models.bookings import Booking, BookingCreate, BookingResponse, StatisticsResponse
from models.users import User
from database.connection import get_session
from models.analytics import AnalyticsData
from models.discount import Discount, DiscountUpdate, DiscountResponse
from services.forecast import SimpleForecast

bookings_router = APIRouter(
    tags=["Bookings"]
)
TIME_SLOTS = [
    "09:00-11:00", "11:00-13:00", "13:00-15:00",
    "15:00-17:00", "17:00-19:00", "19:00-21:00"
]

MACHINE_NUMBERS = [1, 2, 3]


def validate_date_format(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False


@bookings_router.get("/slots-with-discounts")
async def get_available_slots_with_discounts(
    selected_date: str,
    session: Session = Depends(get_session)
) -> dict:
    """
    Получить доступные слоты с информацией о скидках
    (расширенная версия существующего /slots)
    """
    if not validate_date_format(selected_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date"
        )
    
    # Получаем все брони на выбранную дату
    bookings = session.exec(
        select(Booking).where(Booking.date == selected_date)
    ).all()
    
    # Получаем скидки на эту дату
    discounts = session.exec(
        select(Discount).where(
            Discount.date == selected_date,
            Discount.is_active == True
        )
    ).all()
    
    # Создаем словарь скидок для быстрого доступа
    discount_map = {}
    for d in discounts:
        discount_map[d.time_slot] = d.discount_percent
    
    result = {}
    
    for machine in MACHINE_NUMBERS:
        # Получаем занятые слоты для конкретной машины
        booked_slots = [
            booking.time_slot
            for booking in bookings
            if booking.machine_number == machine
        ]
        
        # Получаем свободные слоты
        available_slots = []
        for slot in TIME_SLOTS:
            if slot not in booked_slots:
                slot_info = {
                    "time_slot": slot,
                    "is_available": True
                }
                
                # Добавляем информацию о скидке
                if slot in discount_map:
                    slot_info["discount"] = discount_map[slot]
                    slot_info["price_with_discount"] = f"со скидкой {discount_map[slot]}%"
                else:
                    slot_info["discount"] = 0
                
                available_slots.append(slot_info)
        
        result[f"machine_{machine}"] = {
            "machine_number": machine,
            "available_slots": available_slots,
            "booked_slots": booked_slots,
        }
    
    return {
        "date": selected_date,
        "machines": result,
        "has_discounts": len(discounts) > 0
    }


# Создание бронирования
@bookings_router.post("/book", response_model=dict)
async def create_booking(
        booking_data: BookingCreate,
        session: Session = Depends(get_session)
) -> dict:

    # Проверка существования пользователя
    user = session.get(User, booking_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with supplied ID does not exist"
        )
    # Проверка формата даты
    if not validate_date_format(booking_data.date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in format DD.MM.YYYY"
        )
    # Проверка временного слота
    if booking_data.time_slot not in TIME_SLOTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid time slot."
        )
    # Проверка номера машины
    if booking_data.machine_number not in MACHINE_NUMBERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid machine number. Available machines: {MACHINE_NUMBERS}"
        )
    # Проверка доступности слота
    existing_booking = session.exec(
        select(Booking).where(
            Booking.date == booking_data.date,
            Booking.time_slot == booking_data.time_slot,
            Booking.machine_number == booking_data.machine_number
        )
    ).first()
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot on selected machine is already booked"
        )
    # Создаем бронирование
    new_booking = Booking(**booking_data.dict())
    session.add(new_booking)
    session.commit()
    session.refresh(new_booking)
    return {
        "message": "Booking created successfully",
        "booking": {
            "id": new_booking.id,
            "user_id": new_booking.user_id,
            "date": new_booking.date,
            "time_slot": new_booking.time_slot,
            "machine_number": new_booking.machine_number,
        }
    }


# Получение бронирований пользователя
@bookings_router.get("/my-bookings/{user_id}", response_model=dict)
async def get_user_bookings(
        user_id: int,
        session: Session = Depends(get_session)
) -> dict:
    # Проверка существования пользователя
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with supplied ID does not exist"
        )

    # Получаем бронирования пользователя
    user_bookings = session.exec(
        select(Booking).where(Booking.user_id == user_id)
    ).all()

    return {
        "user_id": user_id,
        "bookings": [
            {
                "id": b.id,
                "date": b.date,
                "time_slot": b.time_slot,
                "machine_number": b.machine_number,
            }
            for b in user_bookings
        ]
    }


# Удаление бронирования
@bookings_router.delete("/delete/{booking_id}", response_model=dict)
async def cancel_booking(
        booking_id: int,
        session: Session = Depends(get_session)
) -> dict:

    booking = session.get(Booking, booking_id)

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    session.delete(booking)
    session.commit()

    return {
        "message": "Booking deleted successfully",
        "deleted_booking_id": booking_id
    }


# Расписание на день
@bookings_router.get("/schedule/{selected_date}", response_model=dict)
async def get_daily_schedule(
        selected_date: str,
        session: Session = Depends(get_session)
) -> dict:

    if not validate_date_format(selected_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in format DD.MM.YYYY"
        )

    daily_bookings = session.exec(
        select(Booking).where(Booking.date == selected_date)
    ).all()

    # Группируем по машинам
    bookings_by_machine = {}
    for machine in MACHINE_NUMBERS:
        machine_bookings = [
            b for b in daily_bookings
            if b.machine_number == machine
        ]
        bookings_by_machine[f"machine_{machine}"] = [
            {
                "id": b.id,
                "user_id": b.user_id,
                "time_slot": b.time_slot,
            }
            for b in machine_bookings
        ]

    return {
        "date": selected_date,
        "bookings_by_machine": bookings_by_machine,
    }


# Статистика
@bookings_router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
        session: Session = Depends(get_session)
) -> StatisticsResponse:
    all_bookings = session.exec(select(Booking)).all()

    if not all_bookings:
        return StatisticsResponse(
            machine_usage={f"machine_{i}": 0 for i in MACHINE_NUMBERS},
            popular_slots=[],
            #machine_slot_statistics={},
            #total_bookings=0
        )

    # Статистика по машинам
    machine_counts = {machine: 0 for machine in MACHINE_NUMBERS}
    for booking in all_bookings:
        machine_counts[booking.machine_number] += 1

    # Форматируем для вывода
    machine_usage = {}
    total_bookings = len(all_bookings)
    for machine, count in machine_counts.items():
        percentage = (count / total_bookings * 100) if total_bookings > 0 else 0
        machine_usage[f"machine_{machine}"] = {
            "bookings_count": count,
            "percentage": round(percentage, 2),
        }

    # Популярные слоты
    slot_counter = Counter(booking.time_slot for booking in all_bookings)

    popular_slots = []
    for slot, count in slot_counter.most_common():
        percentage = (count / total_bookings * 100) if total_bookings > 0 else 0
        popular_slots.append({
            "time_slot": slot,
            "bookings_count": count,
            "percentage": round(percentage, 2)
        })

    # Статистика по машинам и слотам
    machine_slot_stats = {}
    for machine in MACHINE_NUMBERS:
        machine_bookings = [
            b for b in all_bookings
            if b.machine_number == machine
        ]
        machine_slot_counter = Counter(
            booking.time_slot for booking in machine_bookings
        )

        machine_slots = []
        for slot, count in machine_slot_counter.most_common():
            machine_slots.append({
                "time_slot": slot,
                "bookings_count": count
            })

        machine_slot_stats[f"machine_{machine}"] = {
            "popular_slots": machine_slots[:3]
        }

    return StatisticsResponse(
        machine_usage=machine_usage,
        popular_slots=popular_slots[:5],
        #machine_slot_statistics=machine_slot_stats,
        #total_bookings=total_bookings
    )


# Новый маршрут для заполнения аналитической таблицы
@bookings_router.post("/generate-analytics", response_model=dict)
async def generate_analytics_data(
        session: Session = Depends(get_session)
) -> dict:
    """
    Генерирует денормализованные данные для аналитики
    на основе существующих таблиц User и Booking
    """

    # Очищаем таблицу аналитики перед заполнением (чтобы не было дубликатов)
    session.exec(delete(AnalyticsData))  # Добавьте импорт delete из sqlmodel

    # Получаем все бронирования
    bookings = session.exec(select(Booking)).all()

    analytics_entries = []

    for booking in bookings:
        # Получаем пользователя для этого бронирования
        user = session.get(User, booking.user_id)

        # Преобразуем дату для анализа
        dt = datetime.strptime(booking.date, "%d.%m.%Y")
        day_of_week = dt.weekday()
        month = dt.month
        year = dt.year
        is_weekend = day_of_week >= 5  # 5=суббота, 6=воскресенье

        # Извлекаем начальный час из слота (например, 9 из "09:00-11:00")
        hour_start = int(booking.time_slot.split(':')[0])

        # Создаем полный datetime для Prophet
        slot_datetime = dt.replace(hour=hour_start, minute=0, second=0)

        # Создаем запись для аналитики
        analytics_entry = AnalyticsData(
            booking_id=booking.id,
            booking_date=booking.date,
            booking_time_slot=booking.time_slot,
            booking_machine_number=booking.machine_number,
            booking_created_at=booking.created_at,
            user_id=user.id if user else None,
            user_fio=user.fio if user else None,
            user_phone=user.phone if user else None,
            day_of_week=day_of_week,
            hour_start=hour_start,
            month=month,
            year=year,
            is_weekend=is_weekend,
            slot_datetime=slot_datetime,
            was_booked=True
        )

        analytics_entries.append(analytics_entry)

    # Добавляем все записи в БД
    for entry in analytics_entries:
        session.add(entry)

    session.commit()

    return {
        "message": "Analytics data generated successfully",
        "entries_created": len(analytics_entries)
    }

# ================ МАРШРУТЫ ДЛЯ ПРОГНОЗИРОВАНИЯ ================

@bookings_router.post("/forecast/apply-discounts", response_model=dict)
async def forecast_and_apply_discounts(
    request: dict,
    session: Session = Depends(get_session)
) -> dict:
    """
    Создает прогноз и применяет скидки на основе прогноза
    
    Тело запроса:
    {
        "date": "15.03.2025",           // дата для прогноза
        "period": "day"                  // "day", "week", "month" - для прогноза на период
    }
    
    Если period = "week" или "month", то date - начальная дата
    """
    date_str = request.get("date")
    period = request.get("period", "day")
    
    if not date_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указана дата"
        )
    
    # Проверяем формат даты
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат даты. Используйте ДД.ММ.ГГГГ"
        )
    
    # Создаем сервис прогнозирования
    forecast = SimpleForecast(session)
    
    if period == "day":
        # Прогноз на один день и применение скидок
        result = forecast.apply_discounts_from_prediction(date_str)
        
        # Добавляем сам прогноз для информации
        prediction = forecast.predict_date(date_str)
        result["prediction"] = prediction
        
        return result
        
    elif period == "week":
        # Прогноз на неделю
        predictions = []
        discounts_applied = 0
        
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        for i in range(7):
            current_date = (dt + timedelta(days=i)).strftime("%d.%m.%Y")
            
            # Применяем скидки для каждого дня
            discount_result = forecast.apply_discounts_from_prediction(current_date)
            if "error" not in discount_result:
                discounts_applied += discount_result.get("slots_with_discount", 0)
            
            # Получаем прогноз
            pred = forecast.predict_date(current_date)
            if "error" not in pred:
                predictions.append({
                    "date": current_date,
                    "total_predicted": pred["total_predicted"]
                })
        
        return {
            "message": f"Скидки на неделю с {date_str} созданы",
            "period": "week",
            "start_date": date_str,
            "end_date": (dt + timedelta(days=6)).strftime("%d.%m.%Y"),
            "discounts_applied_total": discounts_applied,
            "predictions": predictions
        }
        
    elif period == "month":
        # Прогноз на месяц (30 дней)
        predictions = []
        discounts_applied = 0
        
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        for i in range(30):
            current_date = (dt + timedelta(days=i)).strftime("%d.%m.%Y")
            
            # Применяем скидки для каждого дня
            discount_result = forecast.apply_discounts_from_prediction(current_date)
            if "error" not in discount_result:
                discounts_applied += discount_result.get("slots_with_discount", 0)
            
            # Получаем прогноз
            pred = forecast.predict_date(current_date)
            if "error" not in pred:
                predictions.append({
                    "date": current_date,
                    "total_predicted": pred["total_predicted"]
                })
        
        return {
            "message": f"Скидки на месяц с {date_str} созданы",
            "period": "month",
            "start_date": date_str,
            "end_date": (dt + timedelta(days=29)).strftime("%d.%m.%Y"),
            "discounts_applied_total": discounts_applied,
            "predictions": predictions
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный период. Используйте 'day', 'week' или 'month'"
        )


@bookings_router.get("/forecast/{date}", response_model=dict)
async def get_forecast(
    date: str,
    session: Session = Depends(get_session)
) -> dict:
    """
    Получить прогноз для конкретной даты (без применения скидок)
    """
    forecast = SimpleForecast(session)
    result = forecast.predict_date(date)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@bookings_router.get("/forecast/week/{start_date}", response_model=dict)
async def get_week_forecast(
    start_date: str,
    session: Session = Depends(get_session)
) -> dict:
    """
    Получить прогноз на неделю (без применения скидок)
    """
    forecast = SimpleForecast(session)
    result = forecast.predict_period(start_date, 7)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@bookings_router.get("/forecast/month/{start_date}", response_model=dict)
async def get_month_forecast(
    start_date: str,
    session: Session = Depends(get_session)
) -> dict:
    """
    Получить прогноз на месяц (без применения скидок)
    """
    forecast = SimpleForecast(session)
    result = forecast.predict_period(start_date, 30)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


# ================ МАРШРУТЫ ДЛЯ УПРАВЛЕНИЯ СКИДКАМИ ================

@bookings_router.get("/discounts", response_model=dict)
async def get_discounts(
    date: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: Session = Depends(get_session)
) -> dict:
    """
    Получить список скидок
    
    Параметры:
    - date: фильтр по дате (ДД.ММ.ГГГГ)
    - is_active: фильтр по активности (true/false)
    """
    query = select(Discount)
    
    if date:
        # Проверяем формат даты
        try:
            datetime.strptime(date, "%d.%m.%Y")
            query = query.where(Discount.date == date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный формат даты"
            )
    
    if is_active is not None:
        query = query.where(Discount.is_active == is_active)
    
    # Сортируем по дате и времени
    query = query.order_by(Discount.date, Discount.time_slot)
    
    discounts = session.exec(query).all()
    
    # Группируем по датам для удобства
    by_date = {}
    for d in discounts:
        if d.date not in by_date:
            by_date[d.date] = []
        by_date[d.date].append({
            "id": d.id,
            "time_slot": d.time_slot,
            "machine_number": d.machine_number,
            "discount_percent": d.discount_percent,
            "is_active": d.is_active,
            "predicted_load": d.predicted_load
        })
    
    return {
        "total": len(discounts),
        "by_date": by_date,
        "discounts": [
            {
                "id": d.id,
                "date": d.date,
                "time_slot": d.time_slot,
                "machine_number": d.machine_number,
                "discount_percent": d.discount_percent,
                "is_active": d.is_active,
                "predicted_load": d.predicted_load
            }
            for d in discounts
        ]
    }


@bookings_router.get("/discounts/{discount_id}", response_model=DiscountResponse)
async def get_discount(
    discount_id: int,
    session: Session = Depends(get_session)
) -> DiscountResponse:
    """
    Получить информацию о конкретной скидке
    """
    discount = session.get(Discount, discount_id)
    
    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Скидка не найдена"
        )
    
    return discount


@bookings_router.put("/discounts/{discount_id}", response_model=dict)
async def update_discount(
    discount_id: int,
    discount_update: DiscountUpdate,
    session: Session = Depends(get_session)
) -> dict:
    """
    Обновить скидку
    """
    discount = session.get(Discount, discount_id)
    
    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Скидка не найдена"
        )
    
    # Обновляем поля
    discount.discount_percent = discount_update.discount_percent
    discount.updated_at = datetime.now()
    
    if discount_update.is_active is not None:
        discount.is_active = discount_update.is_active
    
    if discount_update.machine_number is not None:
        discount.machine_number = discount_update.machine_number
    
    session.add(discount)
    session.commit()
    session.refresh(discount)
    
    return {
        "message": "Скидка обновлена",
        "discount": {
            "id": discount.id,
            "date": discount.date,
            "time_slot": discount.time_slot,
            "discount_percent": discount.discount_percent,
            "is_active": discount.is_active
        }
    }


@bookings_router.delete("/discounts/{discount_id}", response_model=dict)
async def delete_discount(
    discount_id: int,
    session: Session = Depends(get_session)
) -> dict:
    """
    Удалить скидку
    """
    discount = session.get(Discount, discount_id)
    
    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Скидка не найдена"
        )
    
    session.delete(discount)
    session.commit()
    
    return {
        "message": "Скидка удалена",
        "deleted_id": discount_id
    }


@bookings_router.post("/discounts/clear", response_model=dict)
async def clear_discounts(
    date: Optional[str] = None,
    session: Session = Depends(get_session)
) -> dict:
    """
    Очистить скидки
    
    Параметры:
    - date: удалить скидки только на указанную дату (если не указано - все скидки)
    """
    query = select(Discount)
    
    if date:
        try:
            datetime.strptime(date, "%d.%m.%Y")
            query = query.where(Discount.date == date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный формат даты"
            )
    
    discounts = session.exec(query).all()
    count = len(discounts)
    
    for d in discounts:
        session.delete(d)
    
    session.commit()
    
    if date:
        return {
            "message": f"Скидки на {date} удалены",
            "deleted_count": count
        }
    else:
        return {
            "message": "Все скидки удалены",
            "deleted_count": count
        }