from fastapi import FastAPI
from routes.auth import user_router
from routes.bookings import bookings_router

app = FastAPI()

#Регистрируем маршруты
app.include_router(user_router, prefix="/auth")
app.include_router(bookings_router, prefix="/bookings")

@app.get("/")
async def root():
    return {"message": "Добро пожаловать в сервис бронирования стиральной машины!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)