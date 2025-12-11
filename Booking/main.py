from fastapi import FastAPI
from database.connection import create_db_and_tables
from routes.auth import user_router
from routes.bookings import bookings_router

app = FastAPI(title="Cервис бронирования в прачечной", version="1.0.0")

# Регистрируем маршруты
app.include_router(user_router, prefix="/auth")
app.include_router(bookings_router, prefix="/bookings")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    print("Database initialized")


@app.get("/")
async def root():
    return {"message": "Сервис бронирования стиральной машины"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)