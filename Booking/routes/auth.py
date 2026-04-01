from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from pydantic import BaseModel

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
        "user_id": db_user.id,
        "is_admin": db_user.is_admin,
        "fio": db_user.fio
    }


# Получение информации о всех пользователях
@user_router.get("/all", response_model=dict)
async def get_all_users(
        session: Session = Depends(get_session)
) -> dict:

    users = session.exec(select(User)).all()

    susers = []
    for user in users:
        susers.append({
            "id": user.id,
            "fio": user.fio,
            "phone": user.phone
        })

    return {
        "users": susers
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

    # Создаем безопасную копию
    deleted_user_info = {
        "id": user.id,
        "fio": user.fio,
        "phone": user.phone
    }

    return {
        "message": "User deleted successfully",
        "deleted_user": deleted_user_info,
    }


class MakeAdminRequest(BaseModel):
    admin_user_id: int
    target_user_id: int
    is_admin: bool


@user_router.patch("/make-admin", response_model=dict)
async def make_user_admin(
        request: MakeAdminRequest,
        session: Session = Depends(get_session)
):
    # Проверяем, что текущий пользователь (admin_user_id) является администратором
    admin_user = session.get(User, request.admin_user_id)
    if not admin_user or not admin_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can perform this action"
        )

    target_user = session.get(User, request.target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Обновляем поле is_admin
    target_user.is_admin = request.is_admin
    session.add(target_user)
    session.commit()
    session.refresh(target_user)

    return {
        "message": f"User {target_user.fio} admin status set to {request.is_admin}",
        "user_id": target_user.id,
        "is_admin": target_user.is_admin
    }