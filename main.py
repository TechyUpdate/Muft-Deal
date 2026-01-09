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
ADMIN_ID = os.environ.get("ADMIN_ID", "") # Personal Chat ID
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "") # Activity Log Channel (@Username)
SHORTENER_API = os.environ.get("SHORTENER_API", "") 
SUPPORT_USER = os.environ.get("SUPPORT_USER", "Admin")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
MONGO_URI = os.environ.get("MONGO_URI", "")

# --- DATABASE CONNECTION ---
if not MONGO_URI:
    print("❌ Error: MONGO_URI missing hai! Render me add karo.")
    db = None
else:
    try:
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

# --- HELPERS ---
def send_log(text):
    """Activity ko Log Channel me bhejta hai"""
    if LOG_CHANNEL:
        try: bot.send_message(LOG_CHANNEL, text, parse_mode="Markdown")
        except: pass
    elif ADMIN_ID:
        try: bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
        except: pass

def get_user(user_id, username=None):
    if db is None: return {} 
    user = users_col.find_one({"_id": user_id})
    if not user:
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
        # --- NEW USER LOG ---
        send_log(f"🔔 **New User Joined!**\nName: {username or user_id}\nID: `{user_id}`")
    return user

def update_user(user_id, data):
    if db is not None: users_col.update_one({"_id": user_id}, {"$set": data})

def inc_balance(user_id, amount):
    if db is not None: users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})

def inc_ads(user_id):
    if db is not None: users_col.update_one({"_id": user_id}, {"$inc": {"ads_watched": 1}})

def inc_invites(user_id):
    if db is not None: users_col.update_one({"_id": user_id}, {"$inc": {"invites": 1}})

# --- FORCE SUB LOGIC ---
def is_user_member(user_id):
    if not CHANNEL_USERNAME: return True 
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['creator', 'administrator', 'member']
    except:
        return True 

def force_sub_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel (Must)", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Joined (Check)", callback_data="check_join"))
    return markup

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

# --- MAIN HANDLERS ---
if bot:
    @bot.callback_query_handler(func=lambda call: call.data == "check_join")
    def callback_query(call):
        if is_user_member(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "✅ Verified!")
            bot.send_message(call.message.chat.id, "🏠 **Main Menu**", reply_markup=main_menu())
        else:
            bot.answer_callback_query(call.id, "❌ Not Joined Yet!", show_alert=True)

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_id = message.chat.id
        first_name = message.from_user.first_name
        
        # Force Sub Check
        if not is_user_member(user_id):
            bot.send_message(user_id, "⚠️ **Action Required!**\n\nIs bot ko use karne ke liye channel join karein.", reply_markup=force_sub_markup())
            return

        user = get_user(user_id, message.from_user.username)
        
        args = message.text.split()
        if len(args) > 1:
            payload = args[1]
            if payload.startswith("verify_"):
                amount = round(random.uniform(3.50, 5.50), 2)
                inc_balance(user_id, amount)
                inc_ads(user_id)
                bot.reply_to(message, f"✅ **Task Verified!**\n\n💰 **+₹{amount}** Added!")
                # Log Task
                send_log(f"🎬 **Ad Watched**\nUser: {first_name} (`{user_id}`)\nEarned: ₹{amount}")
                return 
            elif payload.isdigit() and int(payload) != user_id:
                referrer_id = int(payload)
                if user['joined_via'] is None:
                    update_user(user_id, {"joined_via": referrer_id})
                    # Referrer Reward
                    ref_user = users_col.find_one({"_id": referrer_id})
                    if ref_user:
                        inc_balance(referrer_id, 40.0)
                        inc_invites(referrer_id)
                        try: bot.send_message(referrer_id, f"🌟 **Referral Bonus!**\n+₹40 (New Friend: {first_name})")
                        except: pass
                        send_log(f"👥 **New Referral**\nRef: `{referrer_id}` invited `{user_id}`")

        bot.reply_to(message, f"👋 Namaste **{first_name}**!\n🤑 **MoneyTube** mein swagat hai!", reply_markup=main_menu())

    @bot.message_handler(func=lambda m: m.text == "▶️ Ad Dekho")
    def watch_video_ad(message):
        user_id = message.chat.id
        if not is_user_member(user_id):
            bot.send_message(user_id, "⚠️ **Pehle Join Karein!**", reply_markup=force_sub_markup())
            return

        token = f"verify_{str(uuid.uuid4())[:6]}"
        final_link = f"{SHORTENER_API}&url=https://t.me/{BOT_USERNAME}?start={token}" if SHORTENER_API else f"https://t.me/{BOT_USERNAME}?start={token}"
        
        msg = bot.reply_to(message, "🔄 **Loading Video Ad...**")
        time.sleep(1.5)
        bot.delete_message(message.chat.id, msg.message_id)

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Watch Video Now", url=final_link))
        bot.reply_to(message, f"🎬 **Video Ad Ready!**\n\n👇 Video shuru karein:", reply_markup=markup)

    @bot.message_handler(func=lambda m: True)
    def all_messages(message):
        user_id = message.chat.id
        if not is_user_member(user_id):
             bot.send_message(user_id, "⚠️ **Pehle Join Karein!**", reply_markup=force_sub_markup())
             return

        user = get_user(user_id)
        text = message.text
        
        if text == "💰 My Wallet":
            bot.reply_to(message, f"💳 **Wallet**\n💰 Balance: ₹{round(user['balance'], 2)}\n📺 Ads: {user['ads_watched']}\n👥 Refers: {user['invites']}")
            
        elif text == "👥 Refer & Earn":
            ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            share_text = quote(f"🔥 Maine is bot se ₹500 kamaye! Tu bhi try kar:\n{ref_link}")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🚀 Share", url=f"https://t.me/share/url?url={ref_link}&text={share_text}"))
            bot.reply_to(message, f"📣 **Refer & Earn**\n\n₹40 per friend!\nLink:\n`{ref_link}`", reply_markup=markup)

        elif text == "🎁 Daily Bonus":
            today = str(date.today())
            if user.get('last_bonus') == today:
                bot.reply_to(message, "❌ Aaj ka bonus le liya hai.")
            else:
                bonus = round(random.uniform(1.00, 5.00), 2)
                inc_balance(user_id, bonus)
                update_user(user_id, {"last_bonus": today})
                bot.reply_to(message, f"🎁 **Daily Bonus!**\n+₹{bonus} added.")
        
        elif text == "👤 My Profile":
             bot.reply_to(message, f"👤 **Profile**\n🆔 `{user_id}`\n📅 Joined: {user.get('joined_date')}\n🏆 {user['status']}", parse_mode="Markdown")

        elif text == "⚙️ Extra":
            bot.reply_to(message, "👇 Option select karein:", reply_markup=extra_menu())

        elif text == "💸 Withdrawal History":
            bot.reply_to(message, "📂 **History**\n\nAbhi koi record nahi.")
            
        elif text == "📢 Updates":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
            bot.reply_to(message, "📢 **Updates**\n\nOfficial channel join karein.", reply_markup=markup)
            
        elif text == "❓ FAQ":
             bot.reply_to(message, "❓ **FAQ**\n\n1️⃣ Ads dekho paise kamao.\n2️⃣ Refer karke ₹40 kamao.\n3️⃣ Min Withdraw: ₹300")
            
        elif text == "🆘 Support":
             bot.reply_to(message, f"📞 **Support**\n\nAdmin: @{SUPPORT_USER}")
            
        elif text == "🏦 Withdraw Money":
            bot.reply_to(message, "🏧 Method select karein:", reply_markup=withdraw_menu())
            
        elif text == "🔙 Main Menu":
            bot.reply_to(message, "🏠 Home", reply_markup=main_menu())

        elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
             if user['balance'] < 300:
                 diff = 300 - user['balance']
                 bot.reply_to(message, f"❌ **Low Balance!**\nNeed ₹300. You have ₹{round(user['balance'], 2)}")
             elif user['invites'] < 5:
                 bot.reply_to(message, f"❌ **Locked!**\nRefer 5 friends first.\nYou invited: {user['invites']}")
             else:
                 # --- LOG CHANNEL ME REQUEST BHEJO ---
                 bot.reply_to(message, "✅ **Request Submitted!**\nAdmin check karke paise bhej denge.")
                 send_log(f"💸 **WITHDRAWAL REQUEST** 💸\n\n👤 User: `{user_id}`\n💰 Amount: ₹{round(user['balance'], 2)}\n🏦 Method: {text}\n\n⚠️ Payment bhejne ke baad balance manually cut karein.")

# --- SERVER ---
@server.route('/')
def home():
    if not MONGO_URI: return "❌ MONGO_URI Missing!"
    return "✅ Bot is Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    if bot: bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
