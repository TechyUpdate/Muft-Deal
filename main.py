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
TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
SHORTENER_API = os.environ.get("SHORTENER_API", "") 
SUPPORT_USER = os.environ.get("SUPPORT_USER", "Admin")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")

# Token Check
if not TOKEN:
    bot = None
else:
    bot = telebot.TeleBot(TOKEN)

server = Flask(__name__)
user_data = {}

# --- DATABASE ---
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
    markup.add("💸 Withdrawal History", "📢 Khabrein")
    markup.add("❓ FAQ", "🆘 Support")
    markup.row("🔙 Main Menu")
    return markup

# --- MAIN LOGIC ---

if bot:
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_id = message.chat.id
        first_name = message.from_user.first_name
        
        user = get_user(user_id)
        user['username'] = message.from_user.username
        
        # New User Alert
        if user['joined_via'] is None and user['ads_watched'] == 0 and user['balance'] == 0:
             if ADMIN_ID:
                try: bot.send_message(ADMIN_ID, f"🔔 New User: {first_name} (`{user_id}`)")
                except: pass

        # Auto-Pay & Refer Logic
        args = message.text.split()
        if len(args) > 1:
            payload = args[1]
            if payload == user.get('pending_token'):
                amount = round(random.uniform(3.50, 5.50), 2)
                user['balance'] += amount
                user['ads_watched'] += 1
                user['pending_token'] = None 
                bot.reply_to(message, f"✅ **Task Verified!**\n\n💰 **+₹{amount}** Added!\nAd dekhne ka shukriya. 🎉")
                return 
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
                       f"Videos dekho aur paise kamao.\n\n"
                       f"👇 Shuru karein:")
        bot.reply_to(message, welcome_msg, reply_markup=main_menu())

    @bot.message_handler(func=lambda m: m.text == "▶️ Ad Dekho")
    def watch_video_ad(message):
        user_id = message.chat.id
        user = get_user(user_id)
        
        msg = bot.reply_to(message, "🔄 **Loading Video Ad...**")
        time.sleep(1.5) 
        
        token = str(uuid.uuid4())[:8]
        user['pending_token'] = token
        destination_link = f"https://t.me/{BOT_USERNAME}?start={token}"
        
        if SHORTENER_API:
            final_link = f"{SHORTENER_API}&url={destination_link}"
        else:
            final_link = destination_link 

        caption = (f"🎬 **Video Ad Ready!**\n\n"
                   f"📊 Rate: ₹3 - ₹5 per video\n"
                   f"⚠️ **Warning:** Video pura load hone dein aur 'Verify' hone tak wait karein.\n\n"
                   f"👇 Video shuru karein:")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("▶️ Watch Video Now", url=final_link))
        
        bot.delete_message(message.chat.id, msg.message_id)
        bot.reply_to(message, caption, reply_markup=markup)

    @bot.message_handler(func=lambda m: True)
    def all_messages(message):
        user_id = message.chat.id
        text = message.text
        user = get_user(user_id)
        
        # --- MAIN MENU ITEMS ---
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
            if user['last_bonus'] == today:
                bot.reply_to(message, "❌ **Oops!** Aaj ka bonus le liya hai.")
            else:
                bonus = round(random.uniform(1.00, 5.00), 2)
                user['balance'] += bonus
                user['last_bonus'] = today
                bot.reply_to(message, f"🎁 **Daily Bonus!**\n+₹{bonus} added.")
        
        elif text == "👤 My Profile":
             bot.reply_to(message, f"👤 **User Profile**\n\n🆔 ID: `{user_id}`\n📅 Joined: {date.today()}\n🏆 Status: {user['status']}", parse_mode="Markdown")

        # --- EXTRA MENU LOGIC ---
        elif text == "⚙️ Extra":
            bot.reply_to(message, "👇 Option select karein:", reply_markup=extra_menu())

        elif text == "💸 Withdrawal History":
            bot.reply_to(message, "📂 **Transaction History**\n\nAbhi koi purana record nahi mila.")
            
        elif text == "📢 Khabrein":
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
            
        # --- WITHDRAWAL LOGIC ---
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
    if not TOKEN: return "❌ Token Missing!"
    return "✅ MoneyTube Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    if bot: bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
