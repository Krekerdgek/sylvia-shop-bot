import os
import logging
from flask import Flask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return 'Test Bot OK'

@app.route('/health')
def health():
    return 'OK'

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("🔥 Webhook received!")
    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
