from flask import Flask, render_template_string, request
import threading
import os
import requests
import json

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID") 

# Absolute path for JSON taaki Render/VPS dono jagah kaam kare
DB_FILE = os.path.join(os.getcwd(), "bot_data.json")

def get_premium_link():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                return data.get("premium_link")
    except Exception as e:
        print(f"File Error: {e}")
    return None

@app.route('/')
def home():
    return "Web Server Active!"

@app.route('/checkout/<session_id>')
def checkout(session_id):
    env_mode = os.environ.get("CASHFREE_ENV", "SANDBOX").lower()
    html_page = """
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"><script src="https://sdk.cashfree.com/js/v3/cashfree.js"></script></head>
    <body style="display:flex; justify-content:center; align-items:center; height:100vh; background:#f0f2f5;">
        <button id="payBtn" style="padding:15px 30px; background:#0088cc; color:white; border:none; border-radius:8px; font-size:18px; font-weight:bold; cursor:pointer;">Pay Now</button>
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
        print("====== WEBHOOK RECEIVED ======")
        
        is_success = False
        if data and data.get("type") == "PAYMENT_SUCCESS_WEBHOOK":
            is_success = True
        elif data and data.get("data", {}).get("order", {}).get("order_status") == "PAID":
            is_success = True

        if is_success:
            order_id = data["data"]["order"]["order_id"]
            user_id = order_id.split('_')[1] 
            
            premium_link = get_premium_link()
            tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            
            if premium_link:
                # 1. User ko link bhejo
                msg_text = f"✅ **Payment Successful!**\n\nWelcome to Premium. Join our private channel here:\n{premium_link}"
                requests.post(tg_url, json={"chat_id": user_id, "text": msg_text})
                
                # 2. Admin ko alert karo
                if ADMIN_ID:
                    admin_msg = f"💰 **Payment Received!**\nUser ID: `{user_id}` ne abhi premium kharida hai."
                    requests.post(tg_url, json={"chat_id": ADMIN_ID, "text": admin_msg})
            else:
                # Agar kisi wajah se link set nahi hua, toh backup plan!
                fallback_msg = "⚠️ Your payment was successful! However, the automated link is not ready. The Admin has been notified and will send you the link shortly."
                requests.post(tg_url, json={"chat_id": user_id, "text": fallback_msg})
                
                if ADMIN_ID:
                    admin_alert = f"🚨 **URGENT:** User `{user_id}` ne payment kar di hai, lekin aapne `/setlink` nahi lagaya tha! Unko turant manual link bhejo."
                    requests.post(tg_url, json={"chat_id": ADMIN_ID, "text": admin_alert})

            return "Success", 200
            
    except Exception as e:
        print(f"WEBHOOK ERROR: {e}")
        
    return "OK", 200

def run_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    threading.Thread(target=run_server).start()
