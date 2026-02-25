import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
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

# Глобальный экземпляр бота
telegram_app = None

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
def init_bot():
    """Создает и настраивает экземпляр бота"""
    global telegram_app
    telegram_app = Application.builder().token(TOKEN).build()
    register_handlers()
    return telegram_app

# ========== Flask Routes ==========
@app.route('/webhook', methods=['POST'])
def webhook():
    """Принимает обновления от Telegram"""
    if request.method == 'POST':
        try:
            update_data = request.get_json(force=True)
            logger.info(f"📥 Получен webhook: {update_data.get('update_id', 'unknown')}")
            
            # Проверяем, что бот инициализирован
            if telegram_app is None:
                logger.error("❌ Бот не инициализирован!")
                return 'Bot not initialized', 500
            
            # Создаем задачу для асинхронной обработки
            asyncio.run_coroutine_threadsafe(
                process_update_async(update_data),
                asyncio.get_event_loop()
            )
            
            return 'OK', 200
        except Exception as e:
            logger.error(f"❌ Ошибка в webhook: {e}", exc_info=True)
            return 'Error', 500
    return 'Method not allowed', 405

async def process_update_async(update_data):
    """Асинхронная обработка обновления"""
    try:
        update = Update.de_json(update_data, telegram_app.bot)
        await telegram_app.process_update(update)
        logger.info(f"✅ Обновление {update.update_id} обработано")
    except Exception as e:
        logger.error(f"❌ Ошибка обработки обновления: {e}", exc_info=True)

@app.route('/health', methods=['GET'])
def health():
    """Health check для Render"""
    return 'OK', 200

@app.route('/', methods=['GET'])
def index():
    return 'Sylvia Bot is running!', 200

@app.route('/test', methods=['GET', 'POST'])
def test():
    """Тестовый эндпоинт"""
    if request.method == 'POST':
        return f"POST received: {request.get_json()}", 200
    return "GET received", 200

# ========== Регистрация обработчиков ==========
def register_handlers():
    """Регистрирует все обработчики команд"""
    try:
        from bot.handlers.start import start_command
        from bot.handlers.profile import profile_command
        from bot.handlers.create_card import create_card_command
        from bot.handlers.my_cards import my_cards_command
        from bot.handlers.stats import stats_command
        from bot.handlers.help import help_command
        from bot.handlers.referral import referral_command
        from bot.handlers.payment import payment_command, stars_handler
        from bot.callback_handlers import callback_handler
        
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(CommandHandler("profile", profile_command))
        telegram_app.add_handler(CommandHandler("create", create_card_command))
        telegram_app.add_handler(CommandHandler("mycards", my_cards_command))
        telegram_app.add_handler(CommandHandler("stats", stats_command))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(CommandHandler("referral", referral_command))
        telegram_app.add_handler(CommandHandler("payment", payment_command))
        telegram_app.add_handler(CallbackQueryHandler(callback_handler))
        telegram_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, stars_handler))
        
        logger.info("✅ Все обработчики успешно зарегистрированы")
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта обработчиков: {e}")
        raise e

# ========== Настройка вебхука ==========
async def setup_webhook():
    """Устанавливает вебхук"""
    try:
        if telegram_app is None:
            logger.error("❌ Бот не инициализирован перед установкой вебхука")
            return
            
        await telegram_app.bot.delete_webhook()
        logger.info("✅ Старый вебхук удален")
        
        await telegram_app.bot.set_webhook(
            url=WEBHOOK_URL,
            allowed_updates=['message', 'callback_query', 'successful_payment'],
            max_connections=40
        )
        logger.info(f"✅ Вебхук установлен: {WEBHOOK_URL}")
        
        webhook_info = await telegram_app.bot.get_webhook_info()
        logger.info(f"ℹ️ Информация о вебхуке: {webhook_info}")
        
        telegram_app.bot_data['REDIRECT_URL'] = os.environ.get("REDIRECT_BASE_URL", RENDER_URL)
        logger.info(f"ℹ️ REDIRECT_URL установлен: {telegram_app.bot_data['REDIRECT_URL']}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка установки вебхука: {e}")
        raise e

# ========== ФУНКЦИЯ ДЛЯ GUNICORN ==========
def create_app():
    """Функция, которую вызывает Gunicorn"""
    global telegram_app
    logger.info("🚀 Gunicorn вызывает create_app()")
    
    if telegram_app is None:
        logger.info("🔄 Инициализация бота...")
        telegram_app = init_bot()
        
        # Запускаем вебхук в фоне
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_webhook())
        logger.info("✅ Бот инициализирован и вебхук установлен")
    
    return app

# ========== ЗАПУСК ==========
def main():
    """Точка входа для локального запуска"""
    logger.info("🚀 Локальный запуск Sylvia Bot...")
    create_app()
    
    # Запускаем Flask
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Запуск Flask на порту {port}")
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)

# Это то, что Gunicorn будет использовать
app = create_app()

if __name__ == "__main__":
    main()
