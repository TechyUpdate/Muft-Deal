import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
import time
import random
import uuid
from datetime import datetime, date
from urllib.parse import quote

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")
ADMIN_ID = os.environ.get("ADMIN_ID")
# Yahan Shortener API (GPLinks/Adsterra) dalna zaroori hai tabhi ads aayenge
SHORTENER_API = os.environ.get("SHORTENER_API") 
SUPPORT_USER = os.environ.get("SUPPORT_USER", "Admin")

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# --- DATABASE ---
user_data = {}

def get_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            'balance': 0.0,
            'invites': 0,
            'ads_watched': 0,
            'last_bonus': None,
            'joined_via': None,
            'status': 'Bronze Member 🥉',
            'pending_token': None,
            'username': None
        }
    return user_data[user_id]

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    # Button ka naam "Ad Dekho" jaisa DhanTube me hai
    markup.row(types.KeyboardButton("▶️ Ad Dekho")) 
    markup.add(types.KeyboardButton("💰 My Wallet"), types.KeyboardButton("👥 Refer & Earn"))
    markup.add(types.KeyboardButton("🎁 Daily Check-in"), types.KeyboardButton("⚙️ Extra"))
    markup.add(types.KeyboardButton("🏦 Withdraw Money"), types.KeyboardButton("🆘 Support"))
    return markup

def withdraw_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer", "🔙 Main Menu")
    return markup

# --- MAIN LOGIC ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    
    if user_id not in user_data:
        if ADMIN_ID:
            try: bot.send_message(ADMIN_ID, f"🔔 New User: {first_name} (`{user_id}`)")
            except: pass
    
    user = get_user(user_id)
    user['username'] = message.from_user.username

    # --- MAGIC VERIFICATION (Auto-Pay) ---
    args = message.text.split()
    if len(args) > 1:
        payload = args[1]
        
        # Scenario 1: User Ad dekh kar wapas aaya
        if payload == user.get('pending_token'):
            # Amount waisa hi random jaisa DhanTube me hota hai (e.g. 4.91)
            amount = round(random.uniform(3.50, 5.50), 2)
            user['balance'] += amount
            user['ads_watched'] += 1
            user['pending_token'] = None 
            
            # DhanTube style success message
            bot.reply_to(message, f"✅ **Aapne ₹ {amount} kamaye!**\nAd dekhne ka dhanyavaad! 🎉")
            return 

        # Scenario 2: Referral
        elif payload.isdigit() and int(payload) != user_id:
            referrer_id = int(payload)
            if user['joined_via'] is None:
                user['joined_via'] = referrer_id
                if referrer_id in user_data:
                    user_data[referrer_id]['balance'] += 40.0
                    user_data[referrer_id]['invites'] += 1
                    try: bot.send_message(referrer_id, f"🌟 **Referral Bonus!**\n+₹40 (New Friend: {first_name})")
                    except: pass

    welcome_msg = (f"👋 Namaste **{first_name}**!\n\n"
                   f"🤑 **MoneyTube** mein swagat hai!\n"
                   f"Videos dekho aur doston ko invite karke paise kamao.\n\n"
                   f"👇 Shuru karein:")
    bot.reply_to(message, welcome_msg, reply_markup=main_menu())

# --- YAHAN HAI WO "VIDEO" WALA JADOO ---
@bot.message_handler(func=lambda m: m.text == "▶️ Ad Dekho")
def watch_video_ad(message):
    user_id = message.chat.id
    user = get_user(user_id)
    
    # 1. Fake "Searching" message (Real feel dene ke liye)
    msg = bot.reply_to(message, "🔄 **Loading Video Ad...**")
    time.sleep(1) # 1 second ka wait
    
    # 2. Token Create karo
    token = str(uuid.uuid4())[:8]
    user['pending_token'] = token
    
    # 3. Link Logic
    destination_link = f"https://t.me/{BOT_USERNAME}?start={token}"
    
    # Agar Shortener API hai to use karo, warna direct (testing)
    if SHORTENER_API:
        final_link = f"{SHORTENER_API}&url={destination_link}"
    else:
        final_link = destination_link

    # 4. DhanTube wali wording copy ki hai
    caption = (f"🎬 **Video Ad Ready!**\n\n"
               f"📊 Rate: ₹3 - ₹5 per video\n"
               f"⚠️ **Warning:** Video khatam hone se pehle band mat karna, nahi toh reward nahi milega.\n\n"
               f"👇 Neeche diye button ko dabao aur ad dekhna shuru karo:")
    
    markup = types.InlineKeyboardMarkup()
    # Button par "Link" nahi "Watch Video" likha hai
    markup.add(types.InlineKeyboardButton("▶️ Watch Video Now", url=final_link))
    
    # Purana "Loading" message delete karke naya bhejo
    bot.delete_message(message.chat.id, msg.message_id)
    bot.reply_to(message, caption, reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.chat.id
    text = message.text
    user = get_user(user_id)
    
    if text == "💰 My Wallet":
        bot.reply_to(message, f"💳 **Wallet**\n💰 Balance: ₹{round(user['balance'], 2)}\n📺 Videos Watched: {user['ads_watched']}")
        
    elif text == "👥 Refer & Earn":
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        share_text = quote(f"🔥 Paisa kamana hai? Is bot se maine ₹500 nikale! Tu bhi try kar:\n{ref_link}")
        share_url = f"https://t.me/share/url?url={ref_link}&text={share_text}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚀 Share with Friends", url=share_url))
        
        bot.reply_to(message, f"📣 **Refer & Earn**\n\nInvite karein aur payein **₹40** har dost par!\n\nLink:\n`{ref_link}`", reply_markup=markup, parse_mode="Markdown")
        
    elif text == "⚙️ Extra":
        bot.reply_to(message, f"⚙️ **Stats**\n\n👀 Total Views: {user['ads_watched']}\n📅 Joined: {date.today()}")

    elif text == "🎁 Daily Bonus": # Purana naam 'Daily Check-in' tha, ab 'Bonus'
        today = str(date.today())
        if user['last_bonus'] == today:
            bot.reply_to(message, "❌ **Oops!** Aaj ka bonus le liya hai.")
        else:
            bonus = round(random.uniform(1.00, 5.00), 2)
            user['balance'] += bonus
            user['last_bonus'] = today
            bot.reply_to(message, f"🎁 **Daily Bonus!**\n+₹{bonus} added.")

    elif text == "🏦 Withdraw Money":
        bot.reply_to(message, "🏧 Method select karein:", reply_markup=withdraw_menu())
        
    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 Home", reply_markup=main_menu())
        
    elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
         bot.reply_to(message, "✅ Withdrawal Request bheji gayi! (Processing...)")

@server.route('/')
def home():
    return "Video Ad Bot Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
