from flask import Flask, render_template_string, request
import threading
import os
import requests
import json

# ==========================================
# ⚙️ HARDCODED VARIABLES (From Image)
# ==========================================
BOT_TOKEN = "8705595678:AAFUhm1tL8fyn_Koy3tm-Msqk71OXjRiZCw"
ADMIN_ID = 6455936378
CASHFREE_ENV = "PRODUCTION"
PORT = 8080
# ==========================================

app = Flask(__name__)
DB_FILE = os.path.join(os.getcwd(), "bot_data.json")

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def update_stats(amount):
    data = load_data()
    stats = data.get("stats", {"total_users": 0, "total_revenue": 0})
    stats["total_users"] += 1
    stats["total_revenue"] += amount
    data["stats"] = stats
    save_data(data)

def create_onetime_link(chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createChatInviteLink"
    payload = {"chat_id": chat_id, "member_limit": 1}
    res = requests.post(url, json=payload).json()
    if res.get("ok"):
        return res["result"]["invite_link"]
    return None

@app.route('/')
def home():
    return "Web Server Active on VPS!"

@app.route('/checkout/<session_id>')
def checkout(session_id):
    env_mode = CASHFREE_ENV.lower()
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
        
        is_success = False
        if data and data.get("type") == "PAYMENT_SUCCESS_WEBHOOK":
            is_success = True
        elif data and data.get("data", {}).get("order", {}).get("order_status") == "PAID":
            is_success = True

        if is_success:
            order_amount = data["data"]["order"].get("order_amount", 0)
            order_id = data["data"]["order"]["order_id"]
            user_id = order_id.split('_')[1] 
            
            db_data = load_data()
            target_channel = db_data.get("target_channel")
            tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            
            if target_channel:
                update_stats(order_amount)
                unique_link = create_onetime_link(target_channel)
                
                if unique_link:
                    msg_text = f"✅ **Payment Successful!**\n\nHere is your unique ONE-TIME use invite link. Do not share it, or it will expire:\n{unique_link}"
                    requests.post(tg_url, json={"chat_id": user_id, "text": msg_text})
                    
                    if ADMIN_ID:
                        requests.post(tg_url, json={"chat_id": ADMIN_ID, "text": f"💰 **Payment Received: ₹{order_amount}**\nUser `{user_id}` generated a one-time link."})
                else:
                    requests.post(tg_url, json={"chat_id": ADMIN_ID, "text": f"🚨 Error: I couldn't generate a link for `{user_id}`. Make sure I have ADMIN rights in the channel."})
            else:
                requests.post(tg_url, json={"chat_id": ADMIN_ID, "text": f"🚨 URGENT: User `{user_id}` paid, but you haven't set the target channel yet!"})

    except Exception as e:
        print(f"WEBHOOK ERROR: {e}")
        
    return "OK", 200

def run_server():
    app.run(host="0.0.0.0", port=PORT)

def keep_alive():
    threading.Thread(target=run_server).start()
