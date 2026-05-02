from flask import Flask, render_template_string, request
import threading
import os
import requests

app = Flask(__name__)

# --- WEBHOOK SETTINGS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Yahan ek khali DB banayenge jise bot.py aakar update karega
db = {} 

@app.route('/')
def home():
    return "Telegram Bot is running on Render!"

@app.route('/checkout/<session_id>')
def checkout(session_id):
    env_mode = os.environ.get("CASHFREE_ENV", "SANDBOX").lower()
    html_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Premium Access Checkout</title>
        <script src="https://sdk.cashfree.com/js/v3/cashfree.js"></script>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; margin: 0; }
            .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; max-width: 400px; width: 90%; }
            .logo { font-size: 40px; margin-bottom: 10px; }
            h2 { color: #333; margin-bottom: 10px; }
            p { color: #666; margin-bottom: 25px; line-height: 1.5; }
            button { background: #0088cc; color: white; border: none; padding: 14px 28px; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%; transition: background 0.3s; }
            button:hover { background: #0077b3; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="logo">💎</div>
            <h2>Complete Payment</h2>
            <p>Click the button below to securely process your payment via Cashfree and unlock premium access.</p>
            <button id="payBtn">Pay Now</button>
        </div>
        <script>
            const cashfree = Cashfree({ mode: "{{ env_mode }}" });
            document.getElementById('payBtn').addEventListener('click', () => {
                cashfree.checkout({ paymentSessionId: "{{ session_id }}" });
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_page, session_id=session_id, env_mode=env_mode)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if data and data.get("data") and data["data"]["order"].get("order_status") == "PAID":
            
            order_id = data["data"]["order"]["order_id"]
            user_id = order_id.split('_')[1] 
            
            # Ab yeh link DB se uthayega jo aapne bot mein set ki hogi!
            premium_link = db.get("premium_link", "Link not updated yet. Please contact admin.")
            
            msg_text = f"✅ Payment Successful! Thank you for purchasing.\n\nHere is your exclusive premium channel link. Please join fast:\n{premium_link}"
            
            tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(tg_url, json={"chat_id": user_id, "text": msg_text})
            
            return "Success", 200
            
    except Exception as e:
        print(f"Webhook error: {e}")
        
    return "Event received", 200

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_server)
    t.start()
