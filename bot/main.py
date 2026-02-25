#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sylvia Bot - адаптированная версия для Render (webhook)
"""

import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    PreCheckoutQueryHandler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация Flask
app = Flask(__name__)

# Токен бота из переменных окружения
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не установлен")

# Создаём приложение Telegram Bot без Updater
telegram_app = Application.builder().token(TOKEN).updater(None).build()

# URL для вебхука (Render подставит автоматически)
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
if not RENDER_URL:
    logger.warning("RENDER_EXTERNAL_URL не установлен, используется localhost для теста")
    RENDER_URL = "http://localhost:5000"

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

# ========== ИМПОРТЫ ОБРАБОТЧИКОВ ==========
# Здесь импортируем твои существующие обработчики
from bot.handlers import start, order, payment, referral, profile, admin
from bot.database.db import init_db

# ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========
def register_handlers():
    """Регистрация всех обработчиков команд"""
    
    # Базовые команды
    telegram_app.add_handler(CommandHandler("start", start.start))
    telegram_app.add_handler(CommandHandler("help", start.help_command))
    
    # Создание визитки
    telegram_app.add_handler(CommandHandler("new", order.new_card))
    telegram_app.add_handler(CallbackQueryHandler(order.handle_template_choice, pattern="^template_"))
    telegram_app.add_handler(CallbackQueryHandler(order.handle_qr_type, pattern="^qr_type_"))
    
    # Профиль и статистика
    telegram_app.add_handler(CommandHandler("profile", profile.show_profile))
    telegram_app.add_handler(CommandHandler("stats", profile.show_stats))
    
    # Реферальная программа
    telegram_app.add_handler(CommandHandler("referral", referral.show_referral))
    telegram_app.add_handler(CommandHandler("balance", referral.show_balance))
    
    # Платежи
    telegram_app.add_handler(CommandHandler("buy", payment.buy))
    telegram_app.add_handler(PreCheckoutQueryHandler(payment.pre_checkout_handler))
    telegram_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, payment.successful_payment_handler))
    
    # Админка
    telegram_app.add_handler(CommandHandler("admin", admin.admin_panel))
    telegram_app.add_handler(CallbackQueryHandler(admin.handle_admin_callback, pattern="^admin_"))
    
    # Текстовые сообщения (для ввода артикулов и т.д.)
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, order.handle_text_input))
    
    logger.info("Обработчики зарегистрированы")

# ========== FLASK ЭНДПОИНТЫ ==========
@app.route("/health", methods=["GET"])
def health():
    """Проверка здоровья для Render"""
    return "OK", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    """Приём обновлений от Telegram"""
    try:
        # Получаем обновление от Telegram
        update_data = request.get_json(force=True)
        update = Update.de_json(update_data, telegram_app.bot)
        
        # Отправляем в очередь обработки
        telegram_app.update_queue.put(update)
        
        logger.debug(f"Получено обновление: {update.update_id}")
        return "OK", 200
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return "Internal Server Error", 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    """Ручная установка вебхука (для отладки)"""
    try:
        bot = Bot(token=TOKEN)
        bot.set_webhook(url=WEBHOOK_URL)
        return f"Webhook установлен на {WEBHOOK_URL}", 200
    except Exception as e:
        return f"Ошибка: {e}", 500

# ========== ЗАПУСК ==========
def main():
    """Точка входа"""
    logger.info("Запуск Sylvia Bot на Render...")
    
    # Инициализация БД
    init_db()
    logger.info("База данных инициализирована")
    
    # Регистрируем обработчики
    register_handlers()
    
    # Сохраняем REDIRECT_URL в данных бота (для QR-кодов)
    telegram_app.bot_data['REDIRECT_URL'] = os.environ.get("REDIRECT_BASE_URL", RENDER_URL)
    
    # Устанавливаем вебхук
    try:
        telegram_app.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Вебхук установлен: {WEBHOOK_URL}")
        
        # Получаем информацию о вебхуке для проверки
        webhook_info = telegram_app.bot.get_webhook_info()
        logger.info(f"Информация о вебхуке: {webhook_info}")
    except Exception as e:
        logger.error(f"Ошибка установки вебхука: {e}")
    
    # Запускаем Flask приложение
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Запуск Flask на порту {port}")
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
