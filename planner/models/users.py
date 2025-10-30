from pydantic import BaseModel
from typing import Optional, List
from models.events import Event

class User(BaseModel):
    email: str
    password: str
    events: Optional[List[Event]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "email": "fastapi@packt.com",
                "password": "strong!!!",
                "events": []
            }
        }

class UserSignIn(BaseModel):
    email: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "fastapi@packt.com",
                "password": "strong!!!"
            }
        }