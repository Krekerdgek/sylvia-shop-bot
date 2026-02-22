# -*- coding: utf-8 -*-

"""
Запросы к базе данных (сложные выборки и операции)
"""

from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
import logging

from bot.database.db import session_scope
from bot.database.models import User, BusinessCard, Scan, Template, Payment, Referral, FavoriteArticle

logger = logging.getLogger(__name__)

# ========== ПОЛЬЗОВАТЕЛИ ==========

def get_or_create_user(telegram_id, username=None, first_name=None, last_name=None):
    """Получить или создать пользователя"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        
        if not user:
            # Генерируем уникальный реферальный код
            import uuid
            referral_code = str(uuid.uuid4())[:8]
            
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                referral_code=referral_code,
                registered_at=datetime.utcnow()
            )
            session.add(user)
            session.flush()
            logger.info(f"Создан новый пользователь: {telegram_id}")
        else:
            # Обновляем данные
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.last_activity = datetime.utcnow()
            
        return user

def get_user_by_telegram_id(telegram_id):
    """Получить пользователя по telegram_id"""
    with session_scope() as session:
        return session.query(User).filter_by(telegram_id=telegram_id).first()

def get_user_by_referral_code(code):
    """Получить пользователя по реферальному коду"""
    with session_scope() as session:
        return session.query(User).filter_by(referral_code=code).first()

def update_user_shop_info(telegram_id, shop_name=None, shop_url_wb=None, shop_url_ozon=None):
    """Обновить информацию о магазине пользователя"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            if shop_name:
                user.shop_name = shop_name
            if shop_url_wb:
                user.shop_url_wb = shop_url_wb
            if shop_url_ozon:
                user.shop_url_ozon = shop_url_ozon
            return True
        return False

def get_all_users(active_only=True):
    """Получить всех пользователей"""
    with session_scope() as session:
        query = session.query(User)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()

def get_user_stats(telegram_id):
    """Получить статистику пользователя"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return None
        
        # Количество визиток
        cards_count = session.query(BusinessCard).filter_by(user_id=user.id).count()
        
        # Количество сканирований
        scans_count = session.query(Scan)\
            .join(BusinessCard, BusinessCard.id == Scan.card_id)\
            .filter(BusinessCard.user_id == user.id)\
            .count()
        
        # Количество рефералов
        referrals_count = session.query(Referral).filter_by(referrer_id=user.id).count()
        
        # Потрачено звезд
        spent_stars = session.query(func.sum(Payment.amount))\
            .filter_by(user_id=user.id, status='success')\
            .scalar() or 0
        
        return {
            'cards_created': cards_count,
            'scans_received': scans_count,
            'referrals_count': referrals_count,
            'spent_stars': spent_stars,
            'balance': user.referral_balance
        }

# ========== ВИЗИТКИ ==========

def create_business_card(telegram_id, template_id, qr_type, token, article=None, collection_id=None):
    """Создать новую визитку"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return None
        
        card = BusinessCard(
            user_id=user.id,
            template_id=template_id,
            qr_type=qr_type,
            target_article=article,
            collection_id=collection_id,
            token=token,
            created_at=datetime.utcnow()
        )
        session.add(card)
        
        # Увеличиваем счетчик созданных визиток
        user.cards_created += 1
        
        session.flush()
        return card.id

def get_user_cards(telegram_id, limit=10):
    """Получить последние визитки пользователя"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return []
        
        return session.query(BusinessCard)\
            .filter_by(user_id=user.id)\
            .order_by(BusinessCard.created_at.desc())\
            .limit(limit)\
            .all()

def get_card_by_token(token):
    """Получить визитку по токену"""
    with session_scope() as session:
        return session.query(BusinessCard).filter_by(token=token).first()

def record_scan(card_id, ip_address, user_agent, referer=None):
    """Записать сканирование визитки"""
    with session_scope() as session:
        scan = Scan(
            card_id=card_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            scanned_at=datetime.utcnow()
        )
        session.add(scan)
        
        # Обновляем счетчик в визитке
        card = session.query(BusinessCard).filter_by(id=card_id).first()
        if card:
            card.scan_count += 1
            card.last_scan = datetime.utcnow()
            
            # Обновляем счетчик у пользователя
            user = session.query(User).filter_by(id=card.user_id).first()
            if user:
                user.scans_received += 1
        
        return True

def get_card_stats(card_id):
    """Получить статистику по конкретной визитке"""
    with session_scope() as session:
        card = session.query(BusinessCard).filter_by(id=card_id).first()
        if not card:
            return None
        
        # Сканирования по дням за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        daily_scans = session.query(
            func.date(Scan.scanned_at).label('date'),
            func.count().label('count')
        ).filter(
            Scan.card_id == card_id,
            Scan.scanned_at >= thirty_days_ago
        ).group_by(
            func.date(Scan.scanned_at)
        ).all()
        
        return {
            'total': card.scan_count,
            'last_scan': card.last_scan,
            'daily': [{'date': str(d.date), 'count': d.count} for d in daily_scans]
        }

# ========== ШАБЛОНЫ ==========

def get_all_templates(active_only=True):
    """Получить все шаблоны"""
    with session_scope() as session:
        query = session.query(Template)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Template.sort_order).all()

def get_template(template_id):
    """Получить шаблон по ID"""
    with session_scope() as session:
        return session.query(Template).filter_by(id=template_id).first()

def get_templates_by_category(category, active_only=True):
    """Получить шаблоны по категории"""
    with session_scope() as session:
        query = session.query(Template).filter_by(category=category)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Template.sort_order).all()

# ========== ИЗБРАННЫЕ АРТИКУЛЫ ==========

def add_favorite_article(telegram_id, article, product_name, marketplace='wb'):
    """Добавить артикул в избранное"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return False
        
        # Проверяем, нет ли уже такого
        existing = session.query(FavoriteArticle).filter_by(
            user_id=user.id,
            article=article
        ).first()
        
        if existing:
            return True  # Уже есть
        
        fav = FavoriteArticle(
            user_id=user.id,
            article=article,
            product_name=product_name,
            marketplace=marketplace,
            added_at=datetime.utcnow()
        )
        session.add(fav)
        return True

def get_favorite_articles(telegram_id, limit=20):
    """Получить избранные артикулы пользователя"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return []
        
        return session.query(FavoriteArticle)\
            .filter_by(user_id=user.id)\
            .order_by(FavoriteArticle.added_at.desc())\
            .limit(limit)\
            .all()

def remove_favorite_article(telegram_id, article):
    """Удалить артикул из избранного"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return False
        
        session.query(FavoriteArticle)\
            .filter_by(user_id=user.id, article=article)\
            .delete()
        return True

# ========== ПЛАТЕЖИ ==========

def create_payment(telegram_id, payment_id, amount, template_id=None):
    """Создать запись о платеже"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return None
        
        payment = Payment(
            user_id=user.id,
            payment_id=payment_id,
            amount=amount,
            status='pending',
            template_id=template_id,
            created_at=datetime.utcnow()
        )
        session.add(payment)
        session.flush()
        return payment.id

def confirm_payment(payment_id):
    """Подтвердить платеж"""
    with session_scope() as session:
        payment = session.query(Payment).filter_by(payment_id=payment_id).first()
        if payment:
            payment.status = 'success'
            payment.completed_at = datetime.utcnow()
            return True
        return False

def get_user_payments(telegram_id, limit=10):
    """Получить историю платежей пользователя"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return []
        
        return session.query(Payment)\
            .filter_by(user_id=user.id)\
            .order_by(Payment.created_at.desc())\
            .limit(limit)\
            .all()

# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========

def process_referral(referral_code, new_user_telegram_id):
    """Обработать переход по реферальной ссылке"""
    with session_scope() as session:
        # Находим пригласившего
        referrer = session.query(User).filter_by(referral_code=referral_code).first()
        if not referrer:
            return False
        
        # Находим нового пользователя
        new_user = session.query(User).filter_by(telegram_id=new_user_telegram_id).first()
        if not new_user:
            return False
        
        # Проверяем, не был ли уже этот пользователь приглашен
        existing = session.query(Referral).filter_by(referee_id=new_user.id).first()
        if existing:
            return False
        
        # Создаем запись о реферале
        referral = Referral(
            referrer_id=referrer.id,
            referee_id=new_user.id,
            created_at=datetime.utcnow()
        )
        session.add(referral)
        
        # Начисляем бонус пригласившему
        referrer.referral_balance += 1
        
        # Сохраняем, кто пригласил нового пользователя
        new_user.referred_by_id = referrer.id
        
        return True

def get_referral_stats(telegram_id):
    """Получить статистику по рефералам"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            return None
        
        # Количество рефералов
        total = session.query(Referral).filter_by(referrer_id=user.id).count()
        
        # Рефералы за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent = session.query(Referral).filter_by(referrer_id=user.id)\
            .filter(Referral.created_at >= thirty_days_ago)\
            .count()
        
        return {
            'total': total,
            'recent': recent,
            'balance': user.referral_balance,
            'code': user.referral_code
        }

def use_referral_balance(telegram_id, amount=1):
    """Использовать бонусные визитки"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user or user.referral_balance < amount:
            return False
        
        user.referral_balance -= amount
        return True

# ========== АДМИНКА ==========

def get_admin_stats():
    """Получить общую статистику для админки"""
    with session_scope() as session:
        # Общее количество пользователей
        total_users = session.query(User).count()
        
        # Активные сегодня
        today = datetime.utcnow().date()
        active_today = session.query(User).filter(
            func.date(User.last_activity) >= today
        ).count()
        
        # Создано визиток
        total_cards = session.query(BusinessCard).count()
        
        # Сканирований всего
        total_scans = session.query(Scan).count()
        
        # Сканирований сегодня
        scans_today = session.query(Scan).filter(
            func.date(Scan.scanned_at) >= today
        ).count()
        
        # Платежи
        total_revenue = session.query(func.sum(Payment.amount))\
            .filter_by(status='success')\
            .scalar() or 0
        
        # Топ пользователей по визиткам
        top_users = session.query(
            User.telegram_id,
            User.username,
            User.cards_created
        ).order_by(User.cards_created.desc()).limit(5).all()
        
        return {
            'users': {
                'total': total_users,
                'active_today': active_today
            },
            'cards': {
                'total': total_cards
            },
            'scans': {
                'total': total_scans,
                'today': scans_today
            },
            'revenue': total_revenue,
            'top_users': [
                {'telegram_id': u[0], 'username': u[1], 'cards': u[2]}
                for u in top_users
            ]
        }
