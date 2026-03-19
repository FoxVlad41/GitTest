from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database.connection import create_db_and_tables
from routes.auth import user_router
from routes.bookings import bookings_router
from routes.analytics_crud import analytics_crud_router

app = FastAPI(title="Сервис бронирования в прачечной", version="2.0.0")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Регистрируем маршруты API
app.include_router(user_router, prefix="/auth")
app.include_router(bookings_router, prefix="/bookings")
app.include_router(analytics_crud_router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    print("Database initialized")


@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)