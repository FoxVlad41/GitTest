from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select

from models.users import User, UserSignIn, UserResponse
from database.connection import get_session

user_router = APIRouter(
    tags=["User"]
)


# Регистрация
@user_router.post("/signup", response_model=dict)
async def sign_new_user(
        user: User,
        session: Session = Depends(get_session)
) -> dict:

    # Проверка: существует ли пользователь с таким телефоном
    existing_user = session.exec(
        select(User).where(User.phone == user.phone)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this phone number already exists"
        )

    # Добавляем нового пользователя
    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "message": "User successfully registered",
        "user_id": user.id
    }


# Авторизация
@user_router.post("/signin", response_model=dict)
async def sign_user_in(
        user: UserSignIn,
        session: Session = Depends(get_session)
) -> dict:
    # Находим пользователя по телефону
    db_user = session.exec(
        select(User).where(User.phone == user.phone)
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist"
        )

    # Проверяем пароль
    if db_user.password != user.password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wrong credential passed"
        )

    return {
        "message": "User signed in successfully",
        "user_id": db_user.id
    }


# Получение информации о всех пользователях
@user_router.get("/all", response_model=dict)
async def get_all_users(
        session: Session = Depends(get_session)
) -> dict:

    users = session.exec(select(User)).all()

    # Преобразуем в безопасный формат (без паролей)
    safe_users = []
    for user in users:
        safe_users.append({
            "id": user.id,
            "fio": user.fio,
            "room": user.room,
            "phone": user.phone
        })

    return {
        "users": safe_users
    }


# Получение информации о конкретном пользователе
@user_router.get("/{user_id}", response_model=dict)
async def get_user(
        user_id: int,
        session: Session = Depends(get_session)
) -> dict:

    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Возвращаем без пароля
    return {
        "user": {
            "id": user.id,
            "fio": user.fio,
            "room": user.room,
            "phone": user.phone
        }
    }


# Удаление пользователя
@user_router.delete("/{user_id}", response_model=dict)
async def delete_user(
        user_id: int,
        session: Session = Depends(get_session)
) -> dict:
    from models.bookings import Booking

    # Находим пользователя
    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Находим и удаляем бронирования пользователя
    bookings = session.exec(
        select(Booking).where(Booking.user_id == user_id)
    ).all()

    # Удаляем бронирования
    for booking in bookings:
        session.delete(booking)

    # Удаляем пользователя
    session.delete(user)
    session.commit()

    # Создаем безопасную копию (без пароля)
    deleted_user_info = {
        "id": user.id,
        "fio": user.fio,
        "room": user.room,
        "phone": user.phone
    }

    return {
        "message": "User deleted successfully",
        "deleted_user": deleted_user_info,
    }