# -*- coding: utf-8 -*-

"""
Обработчики платежей через Telegram Stars
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes, PreCheckoutQueryHandler
import logging
import uuid

from bot.config import PAYMENT_TOKEN
from bot.database.queries import (
    get_user_by_telegram_id, create_payment, confirm_payment,
    get_template, get_all_templates
)

logger = logging.getLogger(__name__)

# Курс: 1 звезда = 1 звезда (Telegram Stars)
STAR_CURRENCY = "XTR"

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать доступные для покупки шаблоны"""
    templates = get_all_templates(active_only=True)
    
    # Фильтруем только платные шаблоны
    paid_templates = [t for t in templates if t.price > 0]
    
    if not paid_templates:
        await update.message.reply_text(
            "💎 В данный момент нет платных шаблонов. Все шаблоны бесплатны!"
        )
        return
    
    text = "💎 **Магазин шаблонов**\n\n"
    text += "Вы можете купить премиум-шаблоны за Telegram Stars:\n\n"
    
    keyboard = []
    
    for template in paid_templates:
        text += f"**{template.name}** — {template.price} ⭐\n"
        text += f"_{template.description}_\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"Купить {template.name} за {template.price} ⭐", 
                callback_data=f"buy_template_{template.id}"
            )
        ])
    
    text += "\nПосле покупки шаблон будет доступен в конструкторе."
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку покупки"""
    query = update.callback_query
    await query.answer()
    
    template_id = int(query.data.split('_')[2])
    template = get_template(template_id)
    
    if not template:
        await query.edit_message_text("❌ Шаблон не найден")
        return
    
    # Сохраняем информацию о покупке
    context.user_data['buy_template_id'] = template_id
    context.user_data['buy_template_name'] = template.name
    context.user_data['buy_template_price'] = template.price
    
    # Показываем подтверждение
    keyboard = [
        [InlineKeyboardButton(f"✅ Оплатить {template.price} ⭐", callback_data="confirm_payment")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="cancel_payment")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💎 **Подтверждение покупки**\n\n"
        f"Шаблон: **{template.name}**\n"
        f"Цена: **{template.price} ⭐**\n\n"
        f"После оплаты шаблон станет доступен для создания визиток.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def confirm_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и отправка счета"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_payment":
        await query.edit_message_text("❌ Покупка отменена.")
        return
    
    # Получаем данные из контекста
    template_id = context.user_data.get('buy_template_id')
    template_name = context.user_data.get('buy_template_name')
    price = context.user_data.get('buy_template_price')
    
    if not all([template_id, template_name, price]):
        await query.edit_message_text("❌ Ошибка: данные покупки не найдены.")
        return
    
    # Генерируем уникальный ID платежа
    payment_id = str(uuid.uuid4())
    context.user_data['payment_id'] = payment_id
    
    # Создаем запись в БД
    telegram_id = update.effective_user.id
    create_payment(telegram_id, payment_id, price, template_id)
    
    # Создаем счет в Telegram Stars
    # Формируем массив цен (для звезд это просто число)
    prices = [LabeledPrice(label=template_name, amount=price)]
    
    # Отправляем счет
    await context.bot.send_invoice(
        chat_id=update.effective_user.id,
        title=f"Покупка шаблона {template_name}",
        description=f"Шаблон для создания визиток. Цена: {price} звезд.",
        payload=payment_id,
        provider_token="",  # Для звезд не нужен
        currency=STAR_CURRENCY,
        prices=prices,
        start_parameter="buy_template",
        need_name=False,
        need_email=False,
        need_phone_number=False,
        need_shipping_address=False,
        is_flexible=False
    )
    
    logger.info(f"Счет отправлен пользователю {telegram_id}, payment_id: {payment_id}")

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка перед оплатой"""
    query = update.pre_checkout_query
    
    # Проверяем, что это наш платеж
    payment_id = query.invoice_payload
    if not payment_id:
        await query.answer(ok=False, error_message="Ошибка: неверный платеж")
        return
    
    # Все хорошо, можно оплачивать
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешного платежа"""
    payment = update.message.successful_payment
    payment_id = payment.invoice_payload
    amount = payment.total_amount
    
    # Подтверждаем платеж в БД
    confirm_payment(payment_id)
    
    # Получаем данные из контекста (если еще есть)
    template_id = context.user_data.get('buy_template_id', 1)
    template_name = context.user_data.get('buy_template_name', 'Шаблон')
    
    # Поздравляем с покупкой
    await update.message.reply_text(
        f"✅ **Оплата прошла успешно!**\n\n"
        f"Шаблон **{template_name}** теперь доступен для создания визиток.\n"
        f"Списано: {amount} ⭐\n\n"
        f"👉 Используйте /new чтобы создать визитку.",
        parse_mode='Markdown'
    )
    
    # Очищаем данные
    context.user_data.pop('buy_template_id', None)
    context.user_data.pop('buy_template_name', None)
    context.user_data.pop('buy_template_price', None)
    
    logger.info(f"Успешный платеж {payment_id} на сумму {amount} звезд")
