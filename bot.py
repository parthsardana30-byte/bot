import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import time
import json
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import requests
import web_server

# ==========================================
# ⚙️ HARDCODED VARIABLES (From Image)
# ==========================================
API_ID = 38566629
API_HASH = "22f957c8cfdf85a181820ee3c643cf92"
BOT_TOKEN = "8705595678:AAFUhm1tL8fyn_Koy3tm-Msqk71OXjRiZCw"
ADMIN_ID = 6455936378

CASHFREE_APP_ID = "1272195adda2ec4975cf813cc985912721"
CASHFREE_SECRET_KEY = "cfsk_ma_prod_db3ab7049ec98e8cceee4bf2703241d5_95a66f9f"
CASHFREE_ENV = "PRODUCTION"

# ⚠️ BAS APNA VPS IP YAHAN DAAL DENA (e.g., http://123.45.67.89:8080)
BASE_URL = "http://YOUR_VPS_IP:8080" 
# ==========================================

app = Client("premium_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DB_FILE = os.path.join(os.getcwd(), "bot_data.json")

# --- INTERNAL MEMORY CACHING LOGIC ---
channel_peer_cache = {}

async def get_cached_peer(client: Client, chat_id):
    if chat_id not in channel_peer_cache:
        peer = await client.resolve_peer(chat_id)
        channel_peer_cache[chat_id] = peer
    return channel_peer_cache[chat_id]
# -------------------------------------

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {}

def save_data(key, value):
    data = load_data()
    data[key] = value
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

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
        "customer_details": {"customer_id": str(user_id), "customer_phone": "9999999999", "customer_name": f"User_{user_id}"},
        "order_amount": amount,
        "order_currency": "INR",
        "order_id": order_id
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return f"{BASE_URL}/checkout/{response.json().get('payment_session_id')}"
    except: pass
    return None

# --- USER HANDLERS ---
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    db_data = load_data()
    current_price = db_data.get("price", 499)
    welcome_msg = db_data.get("welcome_msg", "Welcome! Choose an option below.")
    welcome_img = db_data.get("welcome_image")
    sample_link = db_data.get("sample_link", "https://t.me/your_sample_channel")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👀 Sample Channel", url=sample_link)],
        [InlineKeyboardButton(f"💳 Buy Premium (₹{current_price})", callback_data="buy_premium")]
    ])
    
    if welcome_img:
        await message.reply_photo(photo=welcome_img, caption=welcome_msg, reply_markup=keyboard)
    else:
        await message.reply_text(text=welcome_msg, reply_markup=keyboard)

@app.on_callback_query(filters.regex("buy_premium"))
async def handle_buy(client: Client, callback_query):
    await callback_query.answer("Setting checkout...", show_alert=False)
    current_price = load_data().get("price", 499)
    payment_url = create_cashfree_order(callback_query.from_user.id, current_price)
    
    if payment_url:
        await callback_query.message.reply_text("Your secure checkout page is ready:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Proceed to Payment", url=payment_url)]]))

# --- ADMIN SAAS FEATURES ---

@app.on_message(filters.forwarded & filters.user(ADMIN_ID) & filters.private)
async def set_channel_smart(client, message):
    if message.forward_from_chat and message.forward_from_chat.type == enums.ChatType.CHANNEL:
        channel_id = message.forward_from_chat.id
        
        # Cache peer ID to prevent invalidation error later
        await get_cached_peer(client, channel_id)
        
        save_data("target_channel", channel_id)
        await message.reply_text(f"✅ **Channel Set Successfully!**\nChannel ID: `{channel_id}`\n\nAb bot har user ke liye is channel ka 1-time link generate karega. **MAKE SURE BOT IS ADMIN IN THIS CHANNEL!**")

@app.on_message(filters.command("stats") & filters.user(ADMIN_ID))
async def show_stats(client, message):
    stats = load_data().get("stats", {"total_users": 0, "total_revenue": 0})
    text = f"📊 **BOT STATISTICS**\n\n👥 Total Paid Users: `{stats['total_users']}`\n💰 Total Revenue: `₹{stats['total_revenue']}`"
    await message.reply_text(text)

@app.on_message(filters.command("setimg") & filters.user(ADMIN_ID))
async def set_img(client, message):
    if message.reply_to_message and message.reply_to_message.photo:
        save_data("welcome_image", message.reply_to_message.photo.file_id)
        await message.reply_text("✅ Welcome image updated successfully!")
    else:
        await message.reply_text("❌ Please send a photo first, reply to it, and type `/setimg`")

@app.on_message(filters.command("rmimg") & filters.user(ADMIN_ID))
async def rm_img(client, message):
    save_data("welcome_image", None)
    await message.reply_text("✅ Welcome image removed.")

@app.on_message(filters.command("sendmsg") & filters.user(ADMIN_ID))
async def send_msg(client, message):
    try:
        parts = message.text.split(" ", 2)
        user_id = int(parts[1])
        text_to_send = parts[2]
        await client.send_message(user_id, f"📩 Message from Admin:\n\n{text_to_send}")
        await message.reply_text("✅ Message sent successfully!")
    except:
        await message.reply_text("❌ Usage: `/sendmsg <user_id> <your message>`")

@app.on_message(filters.command("setprice") & filters.user(ADMIN_ID))
async def set_price(client, message):
    try:
        new_price = int(message.text.split(" ")[1])
        save_data("price", new_price)
        await message.reply_text(f"✅ Price updated to ₹{new_price}")
    except: pass

@app.on_message(filters.command("setmsg") & filters.user(ADMIN_ID))
async def set_msg(client, message):
    try:
        new_msg = message.text.split(" ", 1)[1]
        save_data("welcome_msg", new_msg)
        await message.reply_text("✅ Welcome msg updated.")
    except: pass

if __name__ == "__main__":
    web_server.keep_alive()
    print("SaaS Bot Running on VPS with Caching...")
    app.run()
