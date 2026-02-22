# -*- coding: utf-8 -*-

"""
Веб-сервис для редиректов и отслеживания статистики
Flask приложение для обработки переходов по QR-кодам
"""

from flask import Flask, request, redirect, jsonify, render_template_string, abort
import os
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor
from urllib.parse import urlparse
import hashlib
import hmac

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создание Flask приложения
app = Flask(__name__)

# Конфигурация
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    # Для локальной разработки
    DATABASE_URL = 'postgresql://postgres:password@localhost:5432/sylvia'

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SECRET_KEY'] = SECRET_KEY

def get_db_connection():
    """Получение соединения с базой данных"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        return None

@app.route('/health')
def health():
    """Эндпоинт для проверки здоровья сервиса"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/go/<token>')
def track_and_redirect(token):
    """
    Отслеживание перехода по QR-коду и редирект
    """
    # Получаем информацию о визитке по токену
    conn = get_db_connection()
    if not conn:
        return "Service unavailable", 503
    
    try:
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Получаем информацию о визитке
        cur.execute("""
            SELECT 
                bc.id as card_id,
                bc.user_id,
                bc.qr_type,
                bc.target_article,
                bc.collection_id,
                u.shop_url_wb,
                u.shop_url_ozon,
                u.shop_name
            FROM business_cards bc
            JOIN users u ON bc.user_id = u.id
            WHERE bc.token = %s
        """, (token,))
        
        card = cur.fetchone()
        
        if not card:
            logger.warning(f"Токен не найден: {token}")
            return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Ссылка не найдена</title>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        h1 { color: #ff4444; }
                        p { color: #666; }
                    </style>
                </head>
                <body>
                    <h1>🔍 Ссылка не найдена</h1>
                    <p>Возможно, визитка была удалена или ссылка устарела.</p>
                </body>
                </html>
            """), 404
        
        # Сохраняем информацию о сканировании
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        user_agent = request.headers.get('User-Agent', '')
        referer = request.headers.get('Referer', '')
        
        cur.execute("""
            INSERT INTO scans (card_id, ip_address, user_agent, referer)
            VALUES (%s, %s, %s, %s)
        """, (card['card_id'], ip_address, user_agent[:500], referer[:500]))
        
        # Обновляем счетчик в визитке
        cur.execute("""
            UPDATE business_cards 
            SET scan_count = scan_count + 1, last_scan = NOW()
            WHERE id = %s
        """, (card['card_id'],))
        
        conn.commit()
        
        logger.info(f"Переход по токену {token}: card_id={card['card_id']}, ip={ip_address}")
        
        # Определяем целевой URL в зависимости от типа QR
        target_url = determine_target_url(card)
        
        # Добавляем UTM-метки для отслеживания
        target_url = add_utm_params(target_url, card)
        
        # Возвращаем страницу с редиректом (для красоты)
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Переход...</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <meta http-equiv="refresh" content="2;url={{ target_url }}">
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                        text-align: center; 
                        padding: 50px 20px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        min-height: 100vh;
                        margin: 0;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                    }
                    .card {
                        background: rgba(255,255,255,0.1);
                        backdrop-filter: blur(10px);
                        border-radius: 20px;
                        padding: 40px;
                        max-width: 500px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    }
                    h1 { margin-bottom: 20px; font-size: 2em; }
                    p { opacity: 0.9; line-height: 1.6; }
                    .shop-name { 
                        font-size: 1.5em; 
                        font-weight: bold; 
                        margin: 20px 0;
                        color: #ffd700;
                    }
                    .loader {
                        border: 3px solid rgba(255,255,255,0.3);
                        border-top: 3px solid white;
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        animation: spin 1s linear infinite;
                        margin: 30px auto;
                    }
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                    .footer {
                        margin-top: 30px;
                        font-size: 0.9em;
                        opacity: 0.7;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>✨ Спасибо за покупку!</h1>
                    <div class="shop-name">{{ shop_name }}</div>
                    <p>Сейчас вы будете перенаправлены в магазин</p>
                    <div class="loader"></div>
                    <p>Если переход не происходит автоматически, 
                    <a href="{{ target_url }}" style="color: white; font-weight: bold;">нажмите здесь</a></p>
                    <div class="footer">
                        Спасибо, что выбрали нас! ❤️
                    </div>
                </div>
            </body>
            </html>
        """, target_url=target_url, shop_name=card['shop_name'] or 'Магазин')
        
    except Exception as e:
        logger.error(f"Ошибка при обработке токена {token}: {e}")
        return "Internal server error", 500
    finally:
        cur.close()
        conn.close()

def determine_target_url(card):
    """Определение целевого URL в зависимости от типа QR"""
    
    if card['qr_type'] == 'product' and card['target_article']:
        # Ссылка на конкретный товар
        return f"https://www.wildberries.ru/catalog/{card['target_article']}/detail.aspx"
    
    elif card['qr_type'] == 'collection' and card['collection_id']:
        # Ссылка на подборку (можно сделать отдельную страницу)
        return f"/collection/{card['collection_id']}"
    
    elif card['qr_type'] == 'shop':
        # Ссылка на магазин
        if card['shop_url_wb']:
            return card['shop_url_wb']
        elif card['shop_url_ozon']:
            return card['shop_url_ozon']
    
    # По умолчанию - главная Wildberries
    return "https://www.wildberries.ru"

def add_utm_params(url, card):
    """Добавление UTM-меток для отслеживания"""
    # Определяем, есть ли уже параметры
    if '?' in url:
        separator = '&'
    else:
        separator = '?'
    
    # Добавляем UTM-метки
    utm_params = (
        f"utm_source=sylvia_bot"
        f"&utm_medium=qr"
        f"&utm_campaign=card_{card['card_id']}"
        f"&utm_content={card['qr_type']}"
    )
    
    return f"{url}{separator}{utm_params}"

@app.route('/collection/<collection_id>')
def collection_page(collection_id):
    """Страница подборки товаров"""
    # Здесь можно сделать красивую страницу с товарами из подборки
    # Для простоты пока делаем редирект на поиск
    return redirect("https://www.wildberries.ru")

@app.route('/api/stats/<int:user_id>')
def api_user_stats(user_id):
    """API для получения статистики пользователя"""
    days = request.args.get('days', 30, type=int)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 503
    
    try:
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # Общая статистика
        cur.execute("""
            SELECT 
                COUNT(DISTINCT bc.id) as total_cards,
                COUNT(s.id) as total_scans,
                COALESCE(SUM(bc.scan_count), 0) as total_scans_card,
                MAX(bc.last_scan) as last_scan
            FROM business_cards bc
            LEFT JOIN scans s ON bc.id = s.card_id
            WHERE bc.user_id = %s
        """, (user_id,))
        
        total_stats = cur.fetchone()
        
        # Статистика по дням
        cur.execute("""
            SELECT 
                DATE(s.scanned_at) as date,
                COUNT(*) as count
            FROM scans s
            JOIN business_cards bc ON s.card_id = bc.id
            WHERE bc.user_id = %s 
                AND s.scanned_at > NOW() - INTERVAL '%s days'
            GROUP BY DATE(s.scanned_at)
            ORDER BY date DESC
        """, (user_id, days))
        
        daily_stats = cur.fetchall()
        
        # Статистика по визиткам
        cur.execute("""
            SELECT 
                bc.id,
                bc.token,
                bc.qr_type,
                bc.created_at,
                bc.scan_count,
                bc.last_scan
            FROM business_cards bc
            WHERE bc.user_id = %s
            ORDER BY bc.created_at DESC
            LIMIT 10
        """, (user_id,))
        
        cards = cur.fetchall()
        
        return jsonify({
            'user_id': user_id,
            'total': {
                'cards': total_stats['total_cards'] or 0,
                'scans': total_stats['total_scans'] or 0
            },
            'daily': [
                {'date': str(row['date']), 'count': row['count']}
                for row in daily_stats
            ],
            'recent_cards': [
                {
                    'id': row['id'],
                    'token': row['token'],
                    'type': row['qr_type'],
                    'created': row['created_at'].isoformat(),
                    'scans': row['scan_count'],
                    'last_scan': row['last_scan'].isoformat() if row['last_scan'] else None
                }
                for row in cards
            ]
        })
        
    except Exception as e:
        logger.error(f"Ошибка API статистики: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/card/<token>')
def api_card_info(token):
    """API для получения информации о визитке"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 503
    
    try:
        cur = conn.cursor(cursor_factory=DictCursor)
        
        cur.execute("""
            SELECT 
                bc.*,
                u.username,
                u.shop_name
            FROM business_cards bc
            JOIN users u ON bc.user_id = u.id
            WHERE bc.token = %s
        """, (token,))
        
        card = cur.fetchone()
        
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        
        # Получаем последние сканирования
        cur.execute("""
            SELECT 
                scanned_at,
                ip_address,
                user_agent
            FROM scans
            WHERE card_id = %s
            ORDER BY scanned_at DESC
            LIMIT 20
        """, (card['id'],))
        
        scans = cur.fetchall()
        
        return jsonify({
            'id': card['id'],
            'token': card['token'],
            'type': card['qr_type'],
            'created': card['created_at'].isoformat(),
            'scans': card['scan_count'],
            'last_scan': card['last_scan'].isoformat() if card['last_scan'] else None,
            'shop_name': card['shop_name'],
            'recent_scans': [
                {
                    'time': scan['scanned_at'].isoformat(),
                    'ip': scan['ip_address']
                }
                for scan in scans
            ]
        })
        
    except Exception as e:
        logger.error(f"Ошибка API карточки: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.errorhandler(404)
def not_found(e):
    """Обработчик 404 ошибки"""
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Страница не найдена</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { color: #666; }
            </style>
        </head>
        <body>
            <h1>404 - Страница не найдена</h1>
            <p>Запрашиваемая страница не существует.</p>
        </body>
        </html>
    """), 404

@app.errorhandler(500)
def internal_error(e):
    """Обработчик 500 ошибки"""
    logger.error(f"Internal server error: {e}")
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ошибка сервера</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { color: #ff4444; }
            </style>
        </head>
        <body>
            <h1>500 - Ошибка сервера</h1>
            <p>Произошла внутренняя ошибка. Попробуйте позже.</p>
        </body>
        </html>
    """), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Запуск веб-сервиса на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
