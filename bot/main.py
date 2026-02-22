#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sylvia Bot - Главный файл запуска
Конструктор визиток для селлеров Wildberries и Ozon
"""

import logging
import asyncio
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters,
    PreCheckoutQueryHandler
)

from bot.config import BOT_TOKEN, LOG_LEVEL
from bot.database.db import init_db
from bot.handlers import (
    start, order, payment, referral, profile, admin
)
from bot.services.backup import start_backup_scheduler
from bot.services.proxy_rotator import ProxyRotator

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла внутренняя ошибка. Администратор уже уведомлен."
        )

def main():
    """Основная функция запуска бота"""
    logger.info("Запуск Sylvia Bot...")
    
    # Инициализация базы данных
    init_db()
    logger.info("База данных инициализирована")
    
    # Запуск планировщика бэкапов
    start_backup_scheduler()
    logger.info("Планировщик бэкапов запущен")
    
    # Инициализация ротатора прокси
    proxy_rotator = ProxyRotator()
    asyncio.get_event_loop().run_until_complete(proxy_rotator.update_proxies())
    logger.info("Ротатор прокси инициализирован")
    
    # Создание приложения бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Сохраняем ротатор прокси в данных бота
    application.bot_data['proxy_rotator'] = proxy_rotator
    application.bot_data['REDIRECT_URL'] = None  # Будет установлено из config
    
    # Регистрация обработчиков
    register_handlers(application)
    
    # Глобальный обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("Бот готов к работе")
    
    # Запуск бота
    application.run_polling()

def register_handlers(application):
    """Регистрация всех обработчиков"""
    
    # Базовые команды
    application.add_handler(CommandHandler("start", start.start))
    application.add_handler(CommandHandler("help", start.help_command))
    
    # Создание визитки
    application.add_handler(CommandHandler("new", order.new_card))
    application.add_handler(CallbackQueryHandler(order.handle_template_choice, pattern="^template_"))
    application.add_handler(CallbackQueryHandler(order.handle_qr_type, pattern="^qr_type_"))
    application.add_handler(CallbackQueryHandler(order.handle_favorite_choice, pattern="^(save_favorite|continue_without_save)$"))
    
    # Профиль и статистика
    application.add_handler(CommandHandler("profile", profile.show_profile))
    application.add_handler(CommandHandler("stats", profile.show_stats))
    application.add_handler(CallbackQueryHandler(profile.handle_stats_period, pattern="^stats_"))
    
    # Реферальная программа
    application.add_handler(CommandHandler("referral", referral.show_referral))
    application.add_handler(CommandHandler("balance", referral.show_balance))
    application.add_handler(CallbackQueryHandler(referral.handle_referral, pattern="^ref_"))
    
    # Платежи
    application.add_handler(CommandHandler("buy", payment.buy))
    application.add_handler(CallbackQueryHandler(payment.handle_payment, pattern="^buy_"))
    application.add_handler(PreCheckoutQueryHandler(payment.pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, payment.successful_payment_handler))
    
    # Админка
    application.add_handler(CommandHandler("admin", admin.admin_panel))
    application.add_handler(CallbackQueryHandler(admin.handle_admin_callback, pattern="^admin_"))
    
    # Обработчики текста (ввод артикулов и т.д.)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, order.handle_text_input))
    
    logger.info(f"Зарегистрировано обработчиков: {len(application.handlers)}")

if __name__ == '__main__':
    main()
