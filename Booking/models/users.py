from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fio: str = Field(index=True)
    room: str
    phone: str = Field(unique=True, index=True)
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "fio": "Иванов Иван Иванович",
                "room": "205",
                "phone": "+79161234567",
                "password": "password123"
            }
        }

class UserSignIn(SQLModel):
    phone: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+79161234567",
                "password": "password123"
            }
        }

class UserResponse(SQLModel):
    id: int
    fio: str
    room: str
    phone: str
