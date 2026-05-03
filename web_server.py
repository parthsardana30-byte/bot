from flask import Flask, render_template_string, request
import threading
import os
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "Web Server is Active!"

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
        print(data)
        
        # Cashfree se success signal check karna
        is_success = False
        if data and data.get("type") == "PAYMENT_SUCCESS_WEBHOOK":
            is_success = True
        elif data and data.get("data", {}).get("order", {}).get("order_status") == "PAID":
            is_success = True

        if is_success:
            # Order ID se User ID nikalna
            order_id = data["data"]["order"]["order_id"]
            user_id = order_id.split('_')[1] 
            
            # Seedha Render ke Dashboard se link uthayega
            premium_link = os.environ.get("PREMIUM_LINK", "Link not found. Please contact Admin.")
            bot_token = os.environ.get("BOT_TOKEN")
            
            msg_text = f"✅ **Payment Successful!**\n\nThank you for upgrading. Here is your private channel link:\n{premium_link}"
            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            # Telegram API ko message bhejna
            response = requests.post(tg_url, json={"chat_id": user_id, "text": msg_text})
            print("Telegram API Status:", response.status_code)
            print("Telegram API Response:", response.text)
        else:
            print("Payment not successful yet or different webhook type.")
            
    except Exception as e:
        print(f"CRITICAL WEBHOOK ERROR: {e}")
        
    return "OK", 200

def run_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    threading.Thread(target=run_server).start()
