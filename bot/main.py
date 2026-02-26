import os
import logging
import asyncio
import threading
import time
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, filters
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)
logger = logging.getLogger(__name__)

# Инициализация Flask
app = Flask(__name__)

# Токен и URL
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения!")

RENDER_URL = os.environ.get("RENDER_URL", "https://sylvia-shop-bot.onrender.com")
WEBHOOK_URL = f"{RENDER_URL}/webhook"

# Глобальные переменные
telegram_app = None
bot_ready = False  # 👈 Флаг готовности бота

# ========== Flask Routes ==========
@app.route('/webhook', methods=['POST'])
def webhook():
    """Принимает обновления от Telegram"""
    if request.method == 'POST':
        try:
            update_data = request.get_json(force=True)
            logger.info(f"📥 Получен webhook: {update_data.get('update_id', 'unknown')}")
            
            if telegram_app is None or not bot_ready:
                logger.error("❌ Бот ещё не готов!")
                return 'Bot not ready', 503  # 👈 Возвращаем 503, Telegram повторит позже
            
            # Создаем новый event loop для каждого запроса
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(process_update_async(update_data))
            loop.close()
            
            return 'OK', 200
        except Exception as e:
            logger.error(f"❌ Ошибка в webhook: {e}", exc_info=True)
            return 'Error', 500
    return 'Method not allowed', 405

async def process_update_async(update_data):
    """Асинхронная обработка обновления"""
    try:
        logger.info(f"🔄 Начинаем обработку update {update_data.get('update_id', 'unknown')}")
        update = Update.de_json(update_data, telegram_app.bot)
        
        if update.message:
            logger.info(f"💬 Получено сообщение: '{update.message.text}' от {update.effective_user.id}")
        elif update.callback_query:
            logger.info(f"🔘 Получен callback: '{update.callback_query.data}'")
        
        await telegram_app.process_update(update)
        logger.info(f"✅ Обновление {update.update_id} успешно обработано")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки обновления: {e}", exc_info=True)

@app.route('/health', methods=['GET'])
def health():
    """Health check с информацией о состоянии бота"""
    if bot_ready:
        return 'OK', 200
    return 'Bot initializing', 503  # 👈 Render поймёт, что ещё не готов

@app.route('/', methods=['GET'])
def index():
    return 'Sylvia Bot is running!', 200

# ========== Регистрация обработчиков ==========
def register_handlers():
    """Регистрирует все обработчики команд"""
    try:
        from bot.handlers.start import start, help_command
        from bot.handlers.profile import show_profile, show_stats, edit_shop
        from bot.handlers.order import (
            new_card, handle_template_choice, show_qr_type_selection,
            handle_qr_type, handle_text_input, handle_article_input,
            handle_collection_input, handle_favorite_choice,
            generate_card, back_to_templates
        )
        from bot.handlers.payment import (
            buy, handle_payment, confirm_payment_handler,
            pre_checkout_handler, successful_payment_handler
        )
        from bot.handlers.referral import show_referral, show_balance, handle_referral
        from bot.handlers.admin import admin_panel, handle_admin_callback
        
        # Регистрируем команды
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(CommandHandler("profile", show_profile))
        telegram_app.add_handler(CommandHandler("stats", show_stats))
        telegram_app.add_handler(CommandHandler("edit_shop", edit_shop))
        telegram_app.add_handler(CommandHandler("new", new_card))
        telegram_app.add_handler(CommandHandler("create", new_card))
        telegram_app.add_handler(CommandHandler("buy", buy))
        telegram_app.add_handler(CommandHandler("payment", buy))
        telegram_app.add_handler(CommandHandler("referral", show_referral))
        telegram_app.add_handler(CommandHandler("balance", show_balance))
        telegram_app.add_handler(CommandHandler("admin", admin_panel))
        
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
        
        telegram_app.add_handler(CallbackQueryHandler(handle_template_choice, pattern="^template_"))
        telegram_app.add_handler(CallbackQueryHandler(handle_qr_type, pattern="^qr_type_"))
        telegram_app.add_handler(CallbackQueryHandler(handle_favorite_choice, pattern="^(save_favorite|continue_without_save)$"))
        telegram_app.add_handler(CallbackQueryHandler(back_to_templates, pattern="^back_to_templates$"))
        telegram_app.add_handler(CallbackQueryHandler(handle_payment, pattern="^buy_template_"))
        telegram_app.add_handler(CallbackQueryHandler(confirm_payment_handler, pattern="^(confirm|cancel)_payment$"))
        telegram_app.add_handler(CallbackQueryHandler(handle_referral, pattern="^ref_"))
        telegram_app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_"))
        
        telegram_app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
        telegram_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
        
        logger.info("✅ Все обработчики успешно зарегистрированы")
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта обработчиков: {e}")
        raise e  # 👈 Если ошибка - падаем, чтобы Render перезапустил

# ========== Инициализация бота ==========
async def init_bot_async():
    """Асинхронная инициализация бота"""
    global telegram_app, bot_ready
    try:
        telegram_app = Application.builder().token(TOKEN).build()
        register_handlers()
        await telegram_app.initialize()
        
        # Удаляем старый вебхук
        await telegram_app.bot.delete_webhook()
        logger.info("✅ Старый вебхук удален")
        
        # Устанавливаем новый
        await telegram_app.bot.set_webhook(
            url=WEBHOOK_URL,
            allowed_updates=['message', 'callback_query', 'pre_checkout_query', 'successful_payment'],
            max_connections=40
        )
        logger.info(f"✅ Вебхук установлен: {WEBHOOK_URL}")
        
        # Проверяем вебхук
        webhook_info = await telegram_app.bot.get_webhook_info()
        logger.info(f"ℹ️ Информация о вебхуке: {webhook_info}")
        
        telegram_app.bot_data['REDIRECT_URL'] = os.environ.get("REDIRECT_BASE_URL", RENDER_URL)
        logger.info(f"ℹ️ REDIRECT_URL установлен: {telegram_app.bot_data['REDIRECT_URL']}")
        
        bot_ready = True  # 👈 Всё готово!
        logger.info("✅ Бот полностью инициализирован и готов к работе")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка инициализации: {e}", exc_info=True)
        bot_ready = False
        raise e

def init_bot_thread():
    """Функция для потока инициализации бота"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_bot_async())
        # Запускаем loop в фоне для обработки
        loop.run_forever()
    except Exception as e:
        logger.error(f"❌ Поток бота умер: {e}", exc_info=True)

# ========== Функция для Gunicorn ==========
def create_app():
    """Функция, которую вызывает Gunicorn"""
    logger.info("🚀 Gunicorn вызывает create_app()")
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=init_bot_thread, daemon=True)
    bot_thread.start()
    
    # Даём боту время на инициализацию
    logger.info("⏳ Ожидаем инициализацию бота...")
    
    return app

# ========== Точка входа ==========
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Запуск Flask на порту {port}")
    app.run(host="0.0.0.0", port=port, threaded=True)
