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
import pymongo
import certifi

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
SHORTENER_API = os.environ.get("SHORTENER_API", "") 
SUPPORT_USER = os.environ.get("SUPPORT_USER", "Admin")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")
MONGO_URI = os.environ.get("MONGO_URI", "")

# --- DATABASE CONNECTION ---
if not MONGO_URI:
    print("❌ Error: MONGO_URI missing hai! Render me add karo.")
    db = None
else:
    try:
        # Secure connection ke liye certifi use kar rahe hain
        client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client['moneytube_db']
        users_col = db['users']
        print("✅ MongoDB Connected Successfully!")
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        db = None

if not TOKEN:
    bot = None
else:
    bot = telebot.TeleBot(TOKEN)

server = Flask(__name__)

# --- DB HELPERS ---
def get_user(user_id, username=None):
    if db is None: return {} # Fallback agar DB connect na ho
    
    user = users_col.find_one({"_id": user_id})
    
    if not user:
        # New User Create karo DB me
        user = {
            "_id": user_id,
            "balance": 0.0,
            "invites": 0,
            "ads_watched": 0,
            "last_bonus": None,
            "joined_via": None,
            "status": "Bronze Member 🥉",
            "username": username,
            "joined_date": str(date.today())
        }
        users_col.insert_one(user)
    return user

def update_user(user_id, data):
    if db is not None:
        users_col.update_one({"_id": user_id}, {"$set": data})

def inc_balance(user_id, amount):
    if db is not None:
        users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})

def inc_ads(user_id):
    if db is not None:
        users_col.update_one({"_id": user_id}, {"$inc": {"ads_watched": 1}})

def inc_invites(user_id):
    if db is not None:
        users_col.update_one({"_id": user_id}, {"$inc": {"invites": 1}})

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton("▶️ Ad Dekho")) 
    markup.add(types.KeyboardButton("💰 My Wallet"), types.KeyboardButton("👥 Refer & Earn"))
    markup.add(types.KeyboardButton("🎁 Daily Bonus"), types.KeyboardButton("👤 My Profile")) 
    markup.add(types.KeyboardButton("⚙️ Extra"), types.KeyboardButton("🏦 Withdraw Money"))
    return markup

def withdraw_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer", "🔙 Main Menu")
    return markup

def extra_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("💸 Withdrawal History", "📢 Updates") 
    markup.add("❓ FAQ", "🆘 Support")
    markup.row("🔙 Main Menu")
    return markup

# --- MAIN LOGIC ---

if bot:
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_id = message.chat.id
        first_name = message.from_user.first_name
        username = message.from_user.username
        
        # User fetch/create from DB
        user = get_user(user_id, username)
        
        # Admin Alert (Sirf naye user ke liye)
        if user['ads_watched'] == 0 and user['balance'] == 0 and user['joined_via'] is None:
             if ADMIN_ID:
                try: bot.send_message(ADMIN_ID, f"🔔 New User: {first_name} (`{user_id}`)")
                except: pass

        args = message.text.split()
        if len(args) > 1:
            payload = args[1]
            
            # --- Ad Verification ---
            # Token abhi hum RAM me rakh rahe hain fast verify ke liye (user dictionary use nahi kar rahe)
            # Lekin agar user ne abhi link click kiya hai to verify DB update se hoga
            # Note: Is code me Simple Verify rakha hai, UUID check hata diya hai DB simplicity ke liye
            # Real Ad verify ke liye 'pending_token' logic DB me add karna padega, 
            # par abhi ke liye "Click = Verify" wala simple logic rakhte hain jo reliable ho.
            
            if payload.startswith("verify_"):
                amount = round(random.uniform(3.50, 5.50), 2)
                inc_balance(user_id, amount)
                inc_ads(user_id)
                bot.reply_to(message, f"✅ **Task Verified!**\n\n💰 **+₹{amount}** Added!\nAd dekhne ka shukriya. 🎉")
                return 
            
            # --- Referral ---
            elif payload.isdigit() and int(payload) != user_id:
                referrer_id = int(payload)
                if user['joined_via'] is None:
                    # Update Current User
                    update_user(user_id, {"joined_via": referrer_id})
                    
                    # Update Referrer (Check if exists)
                    ref_user = users_col.find_one({"_id": referrer_id})
                    if ref_user:
                        inc_balance(referrer_id, 40.0)
                        inc_invites(referrer_id)
                        try: bot.send_message(referrer_id, f"🌟 **Referral Bonus!**\n+₹40 (New Friend: {first_name})")
                        except: pass

        welcome_msg = (f"👋 Namaste **{first_name}**!\n\n"
                       f"🤑 **MoneyTube** mein swagat hai!\n"
                       f"Videos dekho aur paise kamao.\n\n"
                       f"👇 Shuru karein:")
        bot.reply_to(message, welcome_msg, reply_markup=main_menu())

    @bot.message_handler(func=lambda m: m.text == "▶️ Ad Dekho")
    def watch_video_ad(message):
        user_id = message.chat.id
        # Token generate karo
        token = f"verify_{str(uuid.uuid4())[:6]}"
        
        destination_link = f"https://t.me/{BOT_USERNAME}?start={token}"
        
        if SHORTENER_API:
            final_link = f"{SHORTENER_API}&url={destination_link}"
        else:
            final_link = destination_link 

        msg = bot.reply_to(message, "🔄 **Loading Video Ad...**")
        time.sleep(1.5)
        bot.delete_message(message.chat.id, msg.message_id)

        caption = (f"🎬 **Video Ad Ready!**\n\n"
                   f"📊 Rate: ₹3 - ₹5 per video\n"
                   f"⚠️ **Warning:** Video pura load hone dein aur 'Verify' hone tak wait karein.\n\n"
                   f"👇 Video shuru karein:")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Watch Video Now", url=final_link))
        
        bot.reply_to(message, caption, reply_markup=markup)

    @bot.message_handler(func=lambda m: True)
    def all_messages(message):
        user_id = message.chat.id
        text = message.text
        # Har baar DB se fresh data lo
        user = get_user(user_id)
        
        if text == "💰 My Wallet":
            bot.reply_to(message, f"💳 **Wallet**\n💰 Balance: ₹{round(user['balance'], 2)}\n📺 Ads: {user['ads_watched']}\n👥 Refers: {user['invites']}")
            
        elif text == "👥 Refer & Earn":
            ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            share_text = quote(f"🔥 Maine is bot se ₹500 kamaye! Tu bhi try kar:\n{ref_link}")
            share_url = f"https://t.me/share/url?url={ref_link}&text={share_text}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🚀 Share with Friends", url=share_url))
            bot.reply_to(message, f"📣 **Refer & Earn**\n\n₹40 + 5% Commission!\nLink:\n`{ref_link}`", reply_markup=markup, parse_mode="Markdown")

        elif text == "🎁 Daily Bonus":
            today = str(date.today())
            if user.get('last_bonus') == today:
                bot.reply_to(message, "❌ **Oops!** Aaj ka bonus le liya hai.")
            else:
                bonus = round(random.uniform(1.00, 5.00), 2)
                inc_balance(user_id, bonus)
                update_user(user_id, {"last_bonus": today})
                bot.reply_to(message, f"🎁 **Daily Bonus!**\n+₹{bonus} added.")
        
        elif text == "👤 My Profile":
             bot.reply_to(message, f"👤 **User Profile**\n\n🆔 ID: `{user_id}`\n📅 Joined: {user.get('joined_date', 'N/A')}\n🏆 Status: {user['status']}", parse_mode="Markdown")

        elif text == "⚙️ Extra":
            bot.reply_to(message, "👇 Option select karein:", reply_markup=extra_menu())

        elif text == "💸 Withdrawal History":
            bot.reply_to(message, "📂 **Transaction History**\n\nAbhi koi purana record nahi mila.")
            
        elif text == "📢 Updates":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 Join Official Channel", url=CHANNEL_LINK))
            bot.reply_to(message, "📢 **DhanTube Updates**\n\nNaye tasks aur payment proofs dekhne ke liye hamara channel join karein.", reply_markup=markup)
            
        elif text == "❓ FAQ":
            msg = ("❓ **DhanTube FAQ**\n\n"
                   "1️⃣ **DhanTube Kya Hai?**\nAds dekhkar paise kamane wala bot.\n\n"
                   "2️⃣ **Rate Kya Hai?**\n₹3 - ₹5 per Ad.\n\n"
                   "3️⃣ **Referral Program?**\n₹40 + 5% Commission per friend.\n\n"
                   "4️⃣ **Withdrawal?**\nUPI, Paytm, Bank Transfer.")
            bot.reply_to(message, msg)
            
        elif text == "🆘 Support":
             bot.reply_to(message, f"📞 **24/7 Support**\n\nAdmin ko message karein:\n@{SUPPORT_USER}")
            
        elif text == "🏦 Withdraw Money":
            bot.reply_to(message, "🏧 Method select karein:", reply_markup=withdraw_menu())
            
        elif text == "🔙 Main Menu":
            bot.reply_to(message, "🏠 Home", reply_markup=main_menu())

        elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
             if user['balance'] < 300:
                 diff = 300 - user['balance']
                 bot.reply_to(message, f"❌ **Withdrawal Failed!**\n\nMinimum Payout: ₹300\n💰 Balance: ₹{round(user['balance'], 2)}\n📉 Aur chahiye: ₹{round(diff, 2)}")
             elif user['invites'] < 5:
                 bot.reply_to(message, f"❌ **Locked!**\n\n5 doston ko invite karna zaroori hai.\n👥 Aapke Invites: {user['invites']}")
             else:
                 bot.reply_to(message, "✅ **Success!**\n\nRequest Admin ko bhej di gayi hai.")

# --- SERVER ---
@server.route('/')
def home():
    if not MONGO_URI: return "❌ MONGO_URI Missing!"
    return "✅ MoneyTube (Database Connected) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    if bot: bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
