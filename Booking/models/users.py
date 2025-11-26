from pydantic import BaseModel
#Модель для регистрации пользователей
class User(BaseModel):
    fio: str  #ФИО
    room: str  #Номер комнаты
    phone: str  #Контактный телефон
    password: str  #Пароль
    #Пример для регистрации
    class Config:
        json_schema_extra = {
            "example": {
                "fio": "Иванов Иван Иванович",
                "room": "205",
                "phone": "+79161234567",
                "password": "password"
            }
        }
#Модель для авторизации пользователей
class UserSignIn(BaseModel):
    phone: str  #Телефон
    password: str  #Пароль
    #Пример для авторизации
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+79161234567",
                "password": "password"
            }
        }