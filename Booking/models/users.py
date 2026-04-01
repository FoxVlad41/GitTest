from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fio: str = Field(index=True)
    phone: str = Field(unique=True, index=True)
    password: str
    is_admin: bool = Field(default=False)

    class Config:
        json_schema_extra = {
            "example": {
                "fio": "Иванов Иван Иванович",
                "phone": "+79161234567",
                "password": "password123",
                "is_admin": False
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
    phone: str
