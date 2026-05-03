import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import time
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import requests
import web_server

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

CASHFREE_APP_ID = os.environ.get("CASHFREE_APP_ID")
CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SECRET_KEY")
CASHFREE_ENV = os.environ.get("CASHFREE_ENV", "SANDBOX")

app = Client("premium_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# JSON File ka rasta
DB_FILE = os.path.join(os.getcwd(), "bot_data.json")

# --- DATABASE HANDLER (Data file se padhna aur likhna) ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_data(key, value):
    data = load_data()
    data[key] = value
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

# Defaults
DEFAULT_PRICE = 499
DEFAULT_MSG = "Welcome! Choose an option below to get started."
SAMPLE_LINK = "https://t.me/your_sample_channel"

# --- CASHFREE ORDER GENERATOR ---
def create_cashfree_order(user_id, amount):
    url = "https://sandbox.cashfree.com/pg/orders" if CASHFREE_ENV == "SANDBOX" else "https://api.cashfree.com/pg/orders"
    headers = {
        "accept": "application/json",
        "x-client-id": CASHFREE_APP_ID,
        "x-client-secret": CASHFREE_SECRET_KEY,
        "x-api-version": "2023-08-01",
        "content-type": "application/json"
    }
    order_id = f"order_{user_id}_{int(time.time())}"
    payload = {
        "customer_details": {
            "customer_id": str(user_id),
            "customer_phone": "9999999999", 
            "customer_name": f"User_{user_id}"
        },
        "order_amount": amount,
        "order_currency": "INR",
        "order_id": order_id
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            session_id = response.json().get("payment_session_id")
            base_url = os.environ.get("RENDER_EXTERNAL_URL", "https://bot-k41g.onrender.com")
            return f"{base_url}/checkout/{session_id}"
    except Exception as e:
        print(e)
    return None

# --- USER COMMANDS ---
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    db_data = load_data()
    current_price = db_data.get("price", DEFAULT_PRICE)
    welcome_msg = db_data.get("welcome_msg", DEFAULT_MSG)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👀 Sample Channel", url=SAMPLE_LINK)],
        [InlineKeyboardButton(f"💳 Buy Premium (₹{current_price})", callback_data="buy_premium")]
    ])
    await message.reply_text(text=welcome_msg, reply_markup=keyboard)

@app.on_callback_query(filters.regex("buy_premium"))
async def handle_buy(client: Client, callback_query):
    await callback_query.answer("Setting checkout...", show_alert=False)
    
    current_price = load_data().get("price", DEFAULT_PRICE)
    payment_url = create_cashfree_order(callback_query.from_user.id, current_price)
    
    if payment_url:
        pay_kbd = InlineKeyboardMarkup([[InlineKeyboardButton("Proceed to Payment", url=payment_url)]])
        await callback_query.message.reply_text("Your secure checkout page is ready. Click below to pay:", reply_markup=pay_kbd)
    else:
        await callback_query.message.reply_text("Server error! Could not create order right now.")

# --- ADMIN COMMANDS (Yeh sab ab file mein save honge) ---
@app.on_message(filters.command("setlink") & filters.user(ADMIN_ID))
async def set_link(client, message):
    try:
        new_link = message.text.split(" ", 1)[1]
        save_data("premium_link", new_link)
        await message.reply_text(f"✅ **Premium Link Updated!**\nAb webhook directly JSON file se yeh link uthayega:\n{new_link}")
    except IndexError:
        await message.reply_text("❌ Usage: `/setlink https://t.me/+aapka_link`")

@app.on_message(filters.command("setprice") & filters.user(ADMIN_ID))
async def set_price(client, message):
    try:
        new_price = int(message.text.split(" ")[1])
        save_data("price", new_price)
        await message.reply_text(f"✅ Price permanently updated to ₹{new_price}")
    except:
        await message.reply_text("❌ Usage: `/setprice 500`")

@app.on_message(filters.command("setmsg") & filters.user(ADMIN_ID))
async def set_msg(client, message):
    try:
        new_msg = message.text.split(" ", 1)[1]
        save_data("welcome_msg", new_msg)
        await message.reply_text("✅ Welcome message updated permanently.")
    except IndexError:
        await message.reply_text("❌ Usage: `/setmsg Hello dosto...`")

if __name__ == "__main__":
    web_server.keep_alive()
    print("Bot is running with fully automated JSON Database...")
    app.run()
