from fastapi import FastAPI
from database.connection import settings
from routes.events import event_router
from routes.users import user_router

app = FastAPI()

@app.on_event("startup")
async def startup_db_client():
    await settings.initialize_database()

app.include_router(event_router, prefix="/event")
app.include_router(user_router, prefix="/user")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)