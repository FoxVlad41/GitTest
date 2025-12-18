from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from datetime import datetime
from collections import Counter

from models.bookings import Booking, BookingCreate, BookingResponse, StatisticsResponse
from models.users import User
from database.connection import get_session

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


# Маршрут для получения доступных слотов
@bookings_router.get("/slots")
async def get_available_slots(
        selected_date: str,
        session: Session = Depends(get_session)
) -> dict:

    if not validate_date_format(selected_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date"
        )

    # Получаем все брони на выбранную дату
    bookings = session.exec(
        select(Booking).where(Booking.date == selected_date)
    ).all()

    result = {}

    for machine in MACHINE_NUMBERS:
        # Получаем занятые слоты для конкретной машины
        booked_slots = [
            booking.time_slot
            for booking in bookings
            if booking.machine_number == machine
        ]

        # Получаем свободные слоты для конкретной машины
        available_slots = [
            slot for slot in TIME_SLOTS
            if slot not in booked_slots
        ]

        result[f"machine_{machine}"] = {
            "machine_number": machine,
            "available_slots": available_slots,
            "booked_slots": booked_slots,
        }

    return {
        "date": selected_date,
        "machines": result,
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