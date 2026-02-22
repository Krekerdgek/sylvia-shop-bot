# -*- coding: utf-8 -*-

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    
    # Регистрация
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    language = Column(String(10), default='ru')
    
    # Магазин
    shop_name = Column(String(255))
    shop_url_wb = Column(String(255))
    shop_url_ozon = Column(String(255))
    
    # Статистика
    cards_created = Column(Integer, default=0)
    scans_received = Column(Integer, default=0)
    
    # Реферальная система
    referral_code = Column(String(50), unique=True)
    referred_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referral_balance = Column(Integer, default=0)  # Бонусные визитки
    
    # Настройки
    settings = Column(JSON, default={})
    
    # Связи
    referred_by = relationship("User", remote_side=[id], backref="referrals")
    cards = relationship("BusinessCard", back_populates="owner", cascade="all, delete-orphan")
    favorite_articles = relationship("FavoriteArticle", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    referrals_sent = relationship("Referral", back_populates="referrer", foreign_keys="Referral.referrer_id")
    referrals_received = relationship("Referral", back_populates="referee", foreign_keys="Referral.referee_id")
    
    def __repr__(self):
        return f"<User(id={self.telegram_id}, username={self.username})>"
    
    def generate_referral_code(self):
        """Генерация уникального реферального кода"""
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4())[:8]
        return self.referral_code

class BusinessCard(Base):
    __tablename__ = 'business_cards'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    template_id = Column(Integer, default=1)
    
    # Параметры QR
    qr_type = Column(String(20), default='shop')  # 'product', 'collection', 'shop'
    target_article = Column(String(50), nullable=True)  # Для product
    collection_id = Column(String(50), nullable=True)  # Для collection
    
    # Уникальный токен для отслеживания
    token = Column(String(50), unique=True, nullable=False, index=True)
    
    # Статистика
    scan_count = Column(Integer, default=0)
    last_scan = Column(DateTime, nullable=True)
    
    # Связи
    owner = relationship("User", back_populates="cards")
    scans = relationship("Scan", back_populates="card", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BusinessCard(id={self.id}, token={self.token}, scans={self.scan_count})>"

class Scan(Base):
    __tablename__ = 'scans'
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('business_cards.id'), nullable=False, index=True)
    
    # Данные сканирования
    scanned_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    referer = Column(String(255))
    
    # Связи
    card = relationship("BusinessCard", back_populates="scans")
    
    def __repr__(self):
        return f"<Scan(id={self.id}, card={self.card_id}, time={self.scanned_at})>"

class Template(Base):
    __tablename__ = 'templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    
    # Файлы
    preview_path = Column(String(255))  # Путь к превью
    file_path = Column(String(255))  # Путь к PSD/шаблону
    
    # Настройки
    is_active = Column(Boolean, default=True)
    price = Column(Integer, default=0)  # 0 - бесплатный, >0 - цена в звездах
    category = Column(String(50), default='general')  # general, wb, ozon, premium
    sort_order = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Template(id={self.id}, name={self.name}, price={self.price})>"

class FavoriteArticle(Base):
    __tablename__ = 'favorite_articles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    article = Column(String(50), nullable=False)
    product_name = Column(String(255))
    marketplace = Column(String(20), default='wb')  # 'wb' или 'ozon'
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="favorite_articles")
    
    def __repr__(self):
        return f"<FavoriteArticle(user={self.user_id}, article={self.article})>"

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Данные платежа
    payment_id = Column(String(100), unique=True)  # ID от Telegram
    amount = Column(Integer)  # В звездах
    currency = Column(String(10), default='XTR')
    status = Column(String(20), default='pending')  # pending, success, failed
    payload = Column(JSON)  # Дополнительные данные
    
    # Что купили
    template_id = Column(Integer, nullable=True)
    quantity = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.payment_id}, amount={self.amount}, status={self.status})>"

class Referral(Base):
    __tablename__ = 'referrals'
    
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    referee_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    reward_given = Column(Boolean, default=False)
    reward_amount = Column(Integer, default=1)  # Сколько бонусов получил
    
    # Связи
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_sent")
    referee = relationship("User", foreign_keys=[referee_id], back_populates="referrals_received")
    
    def __repr__(self):
        return f"<Referral(referrer={self.referrer_id}, referee={self.referee_id})>"
