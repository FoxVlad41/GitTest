from fastapi import APIRouter, HTTPException, status
from models.bookings import Booking, BookingCreate
from datetime import datetime
from routes.auth import users_db  #Импорт массива зарегистрированных пользователей

bookings_router = APIRouter(
    tags=["Bookings"]
)

#Хранилище бронирований
bookings_db = []
#Счетчик для id брони
booking_id = 0

#Доступные временные слоты
TIME_SLOTS = [
    "09:00-11:00", "11:00-13:00", "13:00-15:00",
    "15:00-17:00", "17:00-19:00", "19:00-21:00"
]

#Проверка дата в формате ДД.ММ.ГГГГ
def validate_date_format(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

#Маршрут для вывода занятых и свободных временных слотов на определенную дату
@bookings_router.get("/slots")
async def get_available_slots(selected_date: str) -> dict:
    #Проверка формата даты с помощью заранее заданной функции
    if not validate_date_format(selected_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date. Date must be in format DD.MM.YYYY"
        )
    #Формирование забронированных и незабронированных массивов
    booked_slots = [booking.time_slot for booking in bookings_db if booking.date == selected_date]
    available_slots = [slot for slot in TIME_SLOTS if slot not in booked_slots]
    #ВЫвод массивов
    return {
        "date": selected_date,
        "available_slots": available_slots,
        "booked_slots": booked_slots
    }
#Маршрут для создания бронирования
@bookings_router.post("/book")
async def create_booking(booking_data: BookingCreate) -> dict:
    global booking_id
    
    #Проверка: зарегистрирован ли пользователь
    if booking_data.user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with supplied ID does not exist"
        )
    #Проверка формата даты с помощью заранее заданной функции
    if not validate_date_format(booking_data.date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in format DD.MM.YYYY"
        )
    #Проверка: существует выбранный временной слот
    if booking_data.time_slot not in TIME_SLOTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid time slot."
        )
    #Проверка: свободен ли указанный слот
    existing_booking = False
    for book in bookings_db:
        if book.date == booking_data.date and book.time_slot == booking_data.time_slot:
            existing_booking = True
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot is already booked"
        )
    
    #Создаем бронирование
    booking_id += 1
    new_booking = Booking(
        id=booking_id,
        user_id=booking_data.user_id,
        date=booking_data.date,
        time_slot=booking_data.time_slot
    )
    
    bookings_db.append(new_booking)
    
    return {
        "message": "Booking created successfully",
        "booking": new_booking
    }

#Маршрут для вывода бронирований определенного пользователя
@bookings_router.get("/my-bookings/{user_id}")
async def get_user_bookings(user_id: int) -> dict:
    
    #Проверка: зарегистрирован ли пользователь
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with supplied ID does not exist"
        )
    
    user_bookings = [booking for booking in bookings_db if booking.user_id == user_id]
    
    return {
        "user_id": user_id,
        "bookings": user_bookings
    }

#Маршрут для удаления бронирования
@bookings_router.delete("/delete/{booking_id}")
async def cancel_booking(booking_id: int) -> dict:
    for booking in bookings_db:
        if booking.id == booking_id:
            bookings_db.remove(booking)
            return {
                "message": "Booking deleted successfully"
            }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Booking not found"
    )

#Маршрут для получения броней на определенную дату
@bookings_router.get("/schedule/{selected_date}")
async def get_daily_schedule(selected_date: str) -> dict:
    #Проверка формата даты с помощью заранее заданной функции
    if not validate_date_format(selected_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date must be in format DD.MM.YYYY"
        )
    daily_bookings = [booking for booking in bookings_db if booking.date == selected_date]
    return {
        "date": selected_date,
        "schedule": daily_bookings
    }