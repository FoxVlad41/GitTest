from sqlmodel import SQLModel, Session, create_engine
from typing import Generator

# Настройки подключения к базе данных
SQLITE_DB_NAME = "booking.db"
DATABASE_URL = f"sqlite:///{SQLITE_DB_NAME}"

# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Логировать SQL запросы
    connect_args={"check_same_thread": False}  # Для SQLite
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session