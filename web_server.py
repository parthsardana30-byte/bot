from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is running on Render!"

def run_server():
    # Render automatically ek PORT assign karta hai, hum use yahan fetch kar rahe hain
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_server)
    t.start()