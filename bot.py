import asyncio
import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import requests
from web_server import keep_alive  # Flask server ko import kiya

# Windows par testing ke liye zaroori loop fix
asyncio.set_event_loop(asyncio.new_event_loop())

# --- SECURE CONFIGURATION (Render Environment Variables se aayega) ---
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0)) # Aapka Telegram User ID

CASHFREE_APP_ID = os.environ.get("CASHFREE_APP_ID")
CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SECRET_KEY")
CASHFREE_ENV = os.environ.get("CASHFREE_ENV", "SANDBOX") # "PRODUCTION" for live

# Initialize Bot
app = Client("premium_channel_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- DATABASE ---
db = {
    "price": 499,
    "welcome_msg": "Welcome! Choose an option below to get started.",
    "welcome_image": None,
    "sample_link": "https://t.me/your_sample_channel",
    "premium_link": "https://t.me/+your_private_invite_link"
}

# --- CASHFREE PAYMENT LINK GENERATOR ---
def create_cashfree_link(user_id, amount):
    # Telegram Buttons ke liye 'Payment Links API' best hoti hai
    url = "https://sandbox.cashfree.com/pg/links" if CASHFREE_ENV == "SANDBOX" else "https://api.cashfree.com/pg/links"
    
    headers = {
        "accept": "application/json",
        "x-client-id": CASHFREE_APP_ID,
        "x-client-secret": CASHFREE_SECRET_KEY,
        "x-api-version": "2023-08-01",
        "content-type": "application/json"
    }
    
    payload = {
        "link_id": f"pay_{user_id}_{int(time.time())}",
        "link_amount": amount,
        "link_currency": "INR",
        "link_purpose": "Premium Channel Access",
        "customer_details": {
            "customer_phone": "9999999999", # Required by Cashfree
            "customer_name": f"User_{user_id}"
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("link_url") # Yeh direct payment link dega
        else:
            print(f"Cashfree Error: {response.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# --- BOT HANDLERS ---
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
    await callback_query.answer("Generating secure payment link...", show_alert=False)
    
    # Generate Link
    payment_link = create_cashfree_link(callback_query.from_user.id, db["price"])
    
    if payment_link:
        pay_kbd = InlineKeyboardMarkup([[InlineKeyboardButton("Pay Now", url=payment_link)]])
        await callback_query.message.reply_text("Click below to complete your payment securely via Cashfree:", reply_markup=pay_kbd)
    else:
        await callback_query.message.reply_text("Server error! Could not generate payment link right now. Please tell admin.")

# --- ADMIN COMMANDS ---
@app.on_message(filters.command("setprice") & filters.user(ADMIN_ID))
async def set_price(client, message):
    try:
        new_price = int(message.text.split(" ")[1])
        db["price"] = new_price
        await message.reply_text(f"✅ Price updated to ₹{new_price}")
    except:
        await message.reply_text("Usage: /setprice 500")

@app.on_message(filters.command("setmsg") & filters.user(ADMIN_ID))
async def set_msg(client, message):
    new_msg = message.text.replace("/setmsg ", "", 1)
    db["welcome_msg"] = new_msg
    await message.reply_text("✅ Welcome message updated.")

if __name__ == "__main__":
    # Pehle Flask Web Server start karein (Render ke liye zaroori)
    keep_alive()
    
    # Phir Telegram Bot start karein
    print("Starting Telegram Bot...")
    app.run()