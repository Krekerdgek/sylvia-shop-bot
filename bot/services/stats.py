# -*- coding: utf-8 -*-

"""
Сервис для сбора и агрегации статистики
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from bot.database.queries import get_admin_stats
from bot.database.db import session_scope
from bot.database.models import Scan, BusinessCard, User

logger = logging.getLogger(__name__)

class StatsService:
    """Сервис статистики"""
    
    @staticmethod
    def get_daily_stats(days=30):
        """Получить статистику по дням"""
        with session_scope() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Сканирования по дням
            scans = session.query(
                Scan.scanned_at.cast(Date).label('date'),
                func.count().label('count')
            ).filter(
                Scan.scanned_at >= start_date
            ).group_by(
                'date'
            ).order_by('date').all()
            
            # Новые пользователи по дням
            users = session.query(
                User.registered_at.cast(Date).label('date'),
                func.count().label('count')
            ).filter(
                User.registered_at >= start_date
            ).group_by(
                'date'
            ).order_by('date').all()
            
            # Новые визитки по дням
            cards = session.query(
                BusinessCard.created_at.cast(Date).label('date'),
                func.count().label('count')
            ).filter(
                BusinessCard.created_at >= start_date
            ).group_by(
                'date'
            ).order_by('date').all()
            
            return {
                'scans': [{'date': str(s[0]), 'count': s[1]} for s in scans],
                'users': [{'date': str(u[0]), 'count': u[1]} for u in users],
                'cards': [{'date': str(c[0]), 'count': c[1]} for c in cards]
            }
    
    @staticmethod
    def get_top_users(limit=10):
        """Топ пользователей по визиткам"""
        with session_scope() as session:
            users = session.query(
                User.telegram_id,
                User.username,
                User.cards_created
            ).order_by(
                User.cards_created.desc()
            ).limit(limit).all()
            
            return [
                {
                    'telegram_id': u[0],
                    'username': u[1],
                    'cards': u[2]
                }
                for u in users
            ]
    
    @staticmethod
    def get_top_cards(limit=10):
        """Топ визиток по сканированиям"""
        with session_scope() as session:
            cards = session.query(
                BusinessCard.id,
                BusinessCard.token,
                BusinessCard.scan_count,
                User.telegram_id,
                User.username
            ).join(
                User, BusinessCard.user_id == User.id
            ).order_by(
                BusinessCard.scan_count.desc()
            ).limit(limit).all()
            
            return [
                {
                    'card_id': c[0],
                    'token': c[1],
                    'scans': c[2],
                    'user_id': c[3],
                    'username': c[4]
                }
                for c in cards
            ]
    
    @staticmethod
    def get_hourly_stats(hours=24):
        """Почасовая статистика"""
        with session_scope() as session:
            start_date = datetime.utcnow() - timedelta(hours=hours)
            
            scans = session.query(
                func.date_trunc('hour', Scan.scanned_at).label('hour'),
                func.count().label('count')
            ).filter(
                Scan.scanned_at >= start_date
            ).group_by(
                'hour'
            ).order_by('hour').all()
            
            return [
                {
                    'hour': s[0].strftime('%Y-%m-%d %H:00'),
                    'count': s[1]
                }
                for s in scans
            ]
    
    @staticmethod
    def get_summary():
        """Общая сводка"""
        stats = get_admin_stats()
        
        # Добавляем дополнительные метрики
        with session_scope() as session:
            # Среднее количество визиток на пользователя
            total_users = stats['users']['total']
            total_cards = stats['cards']['total']
            avg_cards = total_cards / total_users if total_users > 0 else 0
            
            # Конверсия сканирований
            conversion = stats['scans']['total'] / total_cards if total_cards > 0 else 0
            
            stats['averages'] = {
                'avg_cards_per_user': round(avg_cards, 2),
                'avg_scans_per_card': round(conversion, 2)
            }
        
        return stats

# Для совместимости с SQLite
try:
    from sqlalchemy import Date
except:
    from sqlalchemy import String
    Date = String
