# -*- coding: utf-8 -*-

"""
Подключение к базе данных и управление сессиями
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
import logging
from contextlib import contextmanager

from bot.config import DATABASE_URL
from bot.database.models import Base

logger = logging.getLogger(__name__)

# Создание движка базы данных
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=False
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False
    )

# Фабрика сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Scoped session для потокобезопасности
db_session = scoped_session(SessionLocal)

def init_db():
    """Инициализация базы данных (создание таблиц)"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Таблицы БД созданы/проверены")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise

def get_db():
    """Получение сессии базы данных"""
    db = db_session()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def session_scope():
    """Контекстный менеджер для работы с сессией"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка в сессии БД: {e}")
        raise
    finally:
        session.close()

def init_test_data():
    """Инициализация тестовых данных (для разработки)"""
    from bot.database.models import Template, User
    
    with session_scope() as session:
        # Проверяем, есть ли уже шаблоны
        if session.query(Template).count() == 0:
            templates = [
                Template(
                    id=1,
                    name="Базовый",
                    description="Простой и лаконичный дизайн",
                    preview_path="templates/preview_1.png",
                    price=0,
                    category="free",
                    sort_order=1
                ),
                Template(
                    id=2,
                    name="Премиум",
                    description="Элегантный дизайн с золотым тиснением",
                    preview_path="templates/preview_2.png",
                    price=50,
                    category="premium",
                    sort_order=2
                ),
                Template(
                    id=3,
                    name="Wildberries",
                    description="Стиль в цветах Wildberries",
                    preview_path="templates/preview_3.png",
                    price=100,
                    category="wb",
                    sort_order=3
                )
            ]
            session.add_all(templates)
            logger.info("Созданы шаблоны по умолчанию")
