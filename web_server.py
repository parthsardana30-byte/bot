from flask import Flask, render_template_string
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is running on Render!"

@app.route('/checkout/<session_id>')
def checkout(session_id):
    env_mode = os.environ.get("CASHFREE_ENV", "SANDBOX").lower()
    
    # Simple & clean HTML UI with Cashfree JS SDK integration
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
            const cashfree = Cashfree({
                mode: "{{ env_mode }}" 
            });
            
            document.getElementById('payBtn').addEventListener('click', () => {
                cashfree.checkout({
                    paymentSessionId: "{{ session_id }}"
                });
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_page, session_id=session_id, env_mode=env_mode)

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_server)
    t.start()
