import asyncio
# SABSE PEHLE EVENT LOOP FIX AAYEGA
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import requests

# Flask Web Server ko import karke DB link kar rahe hain
import web_server  

# --- SECURE CONFIGURATION ---
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

CASHFREE_APP_ID = os.environ.get("CASHFREE_APP_ID")
CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SECRET_KEY")
CASHFREE_ENV = os.environ.get("CASHFREE_ENV", "SANDBOX")

app = Client("premium_channel_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- DATABASE ---
db = {
    "price": 499,
    "welcome_msg": "Welcome! Choose an option below to get started.",
    "welcome_image": None,
    "sample_link": "https://t.me/your_sample_channel",
    "premium_link": "Link not updated yet. Please contact admin."
}

# Bot ki DB ko Web Server ki DB se jodh diya (Taaki webhook naya link bhej sake)
web_server.db = db

# --- INTERNAL MEMORY CACHING LOGIC (For Channel Management) ---
# Yeh logic Peer ID invalidation error ko rokne ke liye design kiya gaya hai.
channel_peer_cache = {}

async def get_cached_peer(client: Client, chat_id):
    """Retains channel peer IDs in internal memory to prevent invalidation."""
    if chat_id not in channel_peer_cache:
        peer = await client.resolve_peer(chat_id)
        channel_peer_cache[chat_id] = peer
    return channel_peer_cache[chat_id]


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
            
            # Render URL dynamically uthayega
            base_url = os.environ.get("RENDER_EXTERNAL_URL", "https://bot-k41g.onrender.com")
            return f"{base_url}/checkout/{session_id}"
        else:
            print(f"Cashfree Error: {response.text}")
            return None
    except Exception as e:
        print(f"Error making order: {e}")
        return None


# --- BOT HANDLERS (User) ---
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👀 Sample Channel", url=db["sample_link"])],
        [InlineKeyboardButton(f"💳 Buy Premium (₹{db['price']})", callback_data="buy_premium")]
    ])
    
    if db["welcome_image"]:
        await message.reply_photo(photo=db["welcome_image"], caption=db["welcome_msg"], reply_markup=keyboard)
    else:
        await message.reply_text(text=db["welcome_msg"], reply_markup=keyboard)


@app.on_callback_query(filters.regex("buy_premium"))
async def handle_buy(client: Client, callback_query):
    await callback_query.answer("Setting up secure checkout...", show_alert=False)
    
    payment_url = create_cashfree_order(callback_query.from_user.id, db["price"])
    
    if payment_url:
        pay_kbd = InlineKeyboardMarkup([[InlineKeyboardButton("Proceed to Payment", url=payment_url)]])
        await callback_query.message.reply_text("Your secure checkout page is ready. Click below to pay:", reply_markup=pay_kbd)
    else:
        await callback_query.message.reply_text("Server error! Could not create order right now. Please tell admin.")


# --- ADMIN COMMANDS ---
@app.on_message(filters.command("setprice") & filters.user(ADMIN_ID))
async def set_price(client, message):
    try:
        new_price = int(message.text.split(" ")[1])
        db["price"] = new_price
        await message.reply_text(f"✅ Price updated to ₹{new_price}")
    except:
        await message.reply_text("❌ Usage: /setprice 500")

@app.on_message(filters.command("setmsg") & filters.user(ADMIN_ID))
async def set_msg(client, message):
    try:
        new_msg = message.text.split(" ", 1)[1]
        db["welcome_msg"] = new_msg
        await message.reply_text("✅ Welcome message updated.")
    except IndexError:
        await message.reply_text("❌ Usage: /setmsg Naya message yahan likhein")

@app.on_message(filters.command("setlink") & filters.user(ADMIN_ID))
async def set_link(client, message):
    try:
        new_link = message.text.split(" ", 1)[1]
        db["premium_link"] = new_link
        await message.reply_text(f"✅ Premium Channel Link updated to:\n{new_link}\n\nPayment successful hone par ab logo ko yahi link jayegi.")
    except IndexError:
        await message.reply_text("❌ Usage: /setlink https://t.me/+aapka_link")

@app.on_message(filters.command("setimg") & filters.user(ADMIN_ID))
async def set_img(client, message):
    if message.reply_to_message and message.reply_to_message.photo:
        db["welcome_image"] = message.reply_to_message.photo.file_id
        await message.reply_text("✅ Welcome image set ho gayi hai!")
    else:
        await message.reply_text("❌ Galti: Pehle koi photo bhejein, phir us photo ko reply karke `/setimg` likhein.")

@app.on_message(filters.command("rmimg") & filters.user(ADMIN_ID))
async def rm_img(client, message):
    db["welcome_image"] = None
    await message.reply_text("✅ Welcome image hata di gayi hai.")


if __name__ == "__main__":
    # Flask Web Server ko start karna
    web_server.keep_alive()
    
    print("Starting Telegram Bot with Admin Controls...")
    app.run()
