from fastapi import APIRouter, HTTPException, status
from models.users import User, UserSignIn

user_router = APIRouter(
    tags=["User"]
)

#База данных пользователей
users_db = {}
#Счётчик для ID пользователей
user_id = 0

#Проверка: существует ли пользователь с таким телефоном
def phone_exists(phone: str) -> bool:
    for user_data in users_db.values():
        if user_data["phone"] == phone:
            return True
    return False
#Функция нахождения аккаунта пользователя по телефону
def find_user_by_phone(phone: str):
    """Находит пользователя по телефону"""
    for user_data in users_db.values():
        if user_data["phone"] == phone:
            return user_data
    return None

#Регистрация
@user_router.post("/signup")
async def sign_new_user(user: User) -> dict:
    global user_id
    
    #Проверка: существует ли пользователь с таким телефоном
    user_data = phone_exists(user.phone)
    if user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this phone number already exists"
        ) 

    #Регистрируем нового пользователя
    user_id += 1
    users_db[user_id] = {
        "id": user_id,
        "fio": user.fio,
        "room": user.room,
        "phone": user.phone,
        "password": user.password
    }
    
    return {
        "message": "User successfully registered"
    }
#Авторизация
@user_router.post("/signin")
async def sign_user_in(user: UserSignIn) -> dict:
    
    #Проверка: существует ли пользователь с таким телефоном
    user_data = find_user_by_phone(user.phone)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist"
        )
    
    #Проверка: правильный ли пароль
    if user_data["password"] != user.password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wrong credential passed"
        )
    
    return {
        "message": "User signed in successfully",
        "user_id": user_data["id"]
    }

#Получение информации о всех пользователях
@user_router.get("/all")
async def get_all_users() -> dict:
    
    return {
        "total_users": len(users_db),
        "users": list(users_db.values())
    }