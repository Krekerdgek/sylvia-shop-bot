# -*- coding: utf-8 -*-

"""
Автоматическое создание бэкапов базы данных
"""

import os
import shutil
import logging
from datetime import datetime
import schedule
import time
import threading
import subprocess

from bot.config import DATABASE_URL, BACKUP_DIR

logger = logging.getLogger(__name__)

class BackupService:
    """Сервис автоматического бэкапа"""
    
    def __init__(self):
        self.backup_dir = BACKUP_DIR
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self) -> str:
        """
        Создание бэкапа базы данных
        
        Returns:
            Путь к файлу бэкапа
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.sql"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            if DATABASE_URL.startswith('sqlite'):
                # SQLite бэкап - просто копируем файл
                db_path = DATABASE_URL.replace('sqlite:///', '')
                if os.path.exists(db_path):
                    shutil.copy2(db_path, backup_path)
                    logger.info(f"SQLite бэкап создан: {backup_path}")
            
            elif DATABASE_URL.startswith('postgresql'):
                # PostgreSQL бэкап через pg_dump
                # Парсим URL
                # postgresql://user:pass@host:port/dbname
                parts = DATABASE_URL.replace('postgresql://', '').split('@')
                user_pass = parts[0].split(':')
                host_db = parts[1].split('/')
                
                user = user_pass[0]
                password = user_pass[1] if len(user_pass) > 1 else ''
                host_port = host_db[0].split(':')
                host = host_port[0]
                port = host_port[1] if len(host_port) > 1 else '5432'
                dbname = host_db[1]
                
                # Формируем команду pg_dump
                env = os.environ.copy()
                if password:
                    env['PGPASSWORD'] = password
                
                cmd = [
                    'pg_dump',
                    '-h', host,
                    '-p', port,
                    '-U', user,
                    '-d', dbname,
                    '-f', backup_path
                ]
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"PostgreSQL бэкап создан: {backup_path}")
                else:
                    logger.error(f"Ошибка создания бэкапа: {result.stderr}")
                    return None
            
            # Удаляем старые бэкапы (оставляем только 10 последних)
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа: {e}")
            return None
    
    def _cleanup_old_backups(self, keep_last=10):
        """Удаление старых бэкапов"""
        try:
            backups = sorted([
                f for f in os.listdir(self.backup_dir) 
                if f.startswith('backup_') and f.endswith('.sql')
            ])
            
            # Удаляем старые бэкапы
            for backup in backups[:-keep_last]:
                os.remove(os.path.join(self.backup_dir, backup))
                logger.info(f"Удален старый бэкап: {backup}")
                
        except Exception as e:
            logger.error(f"Ошибка при очистке бэкапов: {e}")
    
    def restore_backup(self, backup_path: str) -> bool:
        """Восстановление из бэкапа"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Файл бэкапа не найден: {backup_path}")
                return False
            
            if DATABASE_URL.startswith('sqlite'):
                # Для SQLite просто копируем файл
                db_path = DATABASE_URL.replace('sqlite:///', '')
                shutil.copy2(backup_path, db_path)
                logger.info(f"SQLite восстановлен из: {backup_path}")
                return True
            
            elif DATABASE_URL.startswith('postgresql'):
                # Для PostgreSQL через psql
                parts = DATABASE_URL.replace('postgresql://', '').split('@')
                user_pass = parts[0].split(':')
                host_db = parts[1].split('/')
                
                user = user_pass[0]
                password = user_pass[1] if len(user_pass) > 1 else ''
                host_port = host_db[0].split(':')
                host = host_port[0]
                port = host_port[1] if len(host_port) > 1 else '5432'
                dbname = host_db[1]
                
                env = os.environ.copy()
                if password:
                    env['PGPASSWORD'] = password
                
                cmd = [
                    'psql',
                    '-h', host,
                    '-p', port,
                    '-U', user,
                    '-d', dbname,
                    '-f', backup_path
                ]
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"PostgreSQL восстановлен из: {backup_path}")
                    return True
                else:
                    logger.error(f"Ошибка восстановления: {result.stderr}")
                    return False
            
        except Exception as e:
            logger.error(f"Ошибка при восстановлении: {e}")
            return False

def backup_job():
    """Задача для планировщика"""
    backup_service = BackupService()
    backup_service.create_backup()

def start_backup_scheduler():
    """Запуск планировщика бэкапов"""
    # Создаем бэкап каждый день в 3:00
    schedule.every().day.at("03:00").do(backup_job)
    
    # Сразу создаем первый бэкап
    backup_job()
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
    
    # Запускаем в отдельном потоке
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    
    logger.info("Планировщик бэкапов запущен")
