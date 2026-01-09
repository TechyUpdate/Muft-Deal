import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
import time
import random
import uuid
from datetime import datetime, date, timedelta

# --- CONFIGURATION (Render Environment Variables se aayega) ---
TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME") # Bina @ ke (e.g. PaisaWalaBot)
ADMIN_ID = os.environ.get("ADMIN_ID") # Tera Telegram ID

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# --- DATABASE (Temporary Memory) ---
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
            'pending_token': None, # Ad verification ke liye
            'username': None
        }
    return user_data[user_id]

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    # DhanTube style bada button
    markup.row(types.KeyboardButton("🚀 Start Earning (Ads)"))
    markup.add(types.KeyboardButton("💰 My Wallet"), types.KeyboardButton("👥 Refer & Earn"))
    markup.add(types.KeyboardButton("🎁 Daily Check-in"), types.KeyboardButton("📊 Live Proofs"))
    markup.add(types.KeyboardButton("🏦 Withdraw Money"), types.KeyboardButton("🆘 Support"))
    return markup

def withdraw_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer", "🔙 Main Menu")
    return markup

# --- ADMIN COMMANDS (Sirf tere liye) ---

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    # Security Check: Sirf Admin use kar sake
    if str(message.chat.id) != str(ADMIN_ID):
        return

    total_users = len(user_data)
    total_balance = sum(u['balance'] for u in user_data.values())
    total_ads = sum(u['ads_watched'] for u in user_data.values())
    
    msg = (f"👮‍♂️ **Admin Dashboard**\n\n"
           f"👥 Total Users: {total_users}\n"
           f"💰 Total Balance Distrubuted: ₹{round(total_balance, 2)}\n"
           f"📺 Total Ads Watched: {total_ads}")
    bot.reply_to(message, msg)

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if str(message.chat.id) != str(ADMIN_ID):
        return
    
    msg = message.text.replace('/broadcast', '').strip()
    if not msg:
        bot.reply_to(message, "⚠️ Message to likho! Ex: `/broadcast Hello`")
        return
        
    count = 0
    for uid in user_data:
        try:
            bot.send_message(uid, f"📢 **Announcement:**\n\n{msg}")
            count += 1
        except: pass
    bot.reply_to(message, f"✅ Sent to {count} users.")

# --- MAIN LOGIC ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    # Check if New User
    if user_id not in user_data:
        is_new = True
    else:
        is_new = False
        
    user = get_user(user_id)
    user['username'] = username
    
    # Admin Notification (Jab naya banda aaye)
    if is_new and ADMIN_ID:
        try:
            bot.send_message(ADMIN_ID, f"🔔 **New User Alert!**\nName: {first_name}\nID: `{user_id}`\nUser: @{username}")
        except: pass

    # --- MAGIC LINK CHECKING ---
    args = message.text.split()
    if len(args) > 1:
        payload = args[1]
        
        # Scenario 1: Ad Dekh kar wapas aaya hai
        if payload == user.get('pending_token'):
            amount = round(random.uniform(4.50, 6.50), 2)
            user['balance'] += amount
            user['ads_watched'] += 1
            user['pending_token'] = None # Token expire kar do
            
            bot.reply_to(message, f"✅ **Task Verified!**\n\nAd dekhne ka shukriya.\n💵 **+₹{amount}** Added!\n💼 Wallet: ₹{round(user['balance'], 2)}")
            return # Yahi ruk jao, welcome message mat bhejo

        # Scenario 2: Referral Link se aaya hai
        elif payload.isdigit() and int(payload) != user_id:
            referrer_id = int(payload)
            if user['joined_via'] is None:
                user['joined_via'] = referrer_id
                # Referrer ko paise do (agar wo database me hai)
                if referrer_id in user_data:
                    user_data[referrer_id]['balance'] += 40.0
                    user_data[referrer_id]['invites'] += 1
                    try:
                        bot.send_message(referrer_id, f"🌟 **Referral Bonus!**\nApke link se {first_name} join hua.\n💵 **+₹40.00** Added!")
                    except: pass

    welcome_msg = (f"👋 Namaste **{first_name}**!\n\n"
                   f"💎 **CashFlow Prime** mein swagat hai.\n"
                   f"Ads dekho aur paise kamao!\n\n"
                   f"🏆 **Status:** {user['status']}\n"
                   f"👇 Start karne ke liye niche click karein:")
    bot.reply_to(message, welcome_msg, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Start Earning (Ads)")
def earn_money(message):
    user_id = message.chat.id
    user = get_user(user_id)
    
    # 1. Unique Token Generate karo
    token = str(uuid.uuid4())[:8]
    user['pending_token'] = token
    
    # 2. Link Banao (Redirect wapas bot par hoga)
    # Agar Link Shortener hota to hum yahan shortener ka API use karte
    # Abhi ke liye Direct Link hai:
    target_link = f"https://t.me/{BOT_USERNAME}?start={token}"
    
    # Yahan tum Shortener Link laga sakte ho future mein
    # Ex: final_link = f"https://gplinks.in/api?url={target_link}"
    final_link = target_link 
    
    msg = (f"📺 **New Ad Task**\n\n"
           f"1. Link par click karein.\n"
           f"2. Ad page open hoga.\n"
           f"3. Wahan se wapas aate hi paise add ho jayenge.\n\n"
           f"👇 **Click Here:**")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👉 Watch Ad & Earn", url=final_link))
    
    bot.reply_to(message, msg, reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.chat.id
    text = message.text
    user = get_user(user_id)
    
    if text == "💰 My Wallet":
        bal = round(user['balance'], 2)
        bot.reply_to(message, f"💳 **Dashboard**\n\n💰 Balance: ₹{bal}\n📺 Ads Watched: {user['ads_watched']}\n👥 Invites: {user['invites']}")

    elif text == "👥 Refer & Earn":
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        bot.reply_to(message, f"🤝 **Refer & Earn**\n\nShare karein aur kamayein ₹40 per friend!\n\n🔗 **Your Link:**\n{link}")

    elif text == "🎁 Daily Check-in":
        today = str(date.today())
        if user['last_bonus'] == today:
            # Timer Calculation
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            midnight = datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, hour=0, minute=0, second=0)
            remaining = midnight - now
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            bot.reply_to(message, f"⏳ **Wait!** Next Bonus in: **{hours}h {minutes}m**")
        else:
            bonus = round(random.uniform(5.00, 10.00), 2)
            user['balance'] += bonus
            user['last_bonus'] = today
            bot.reply_to(message, f"🎉 **Daily Bonus!**\n\n+ ₹{bonus} Added!")
            
    elif text == "📊 Live Proofs":
        bot.reply_to(message, "🟢 **Recent Payouts:**\nUser123: ₹500 ✅\nUser99: ₹120 ✅")

    elif text == "🏦 Withdraw Money":
        bot.reply_to(message, "🏧 Select Method:", reply_markup=withdraw_menu())
        
    elif text == "🆘 Support":
        bot.reply_to(message, f"📞 Support ke liye Admin ko message karein.")

    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 Home", reply_markup=main_menu())
        
    # Fake Withdraw Logic
    elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
        if user['invites'] < 10:
             bot.reply_to(message, f"🔒 **Withdrawal Locked**\n\nKam se kam 10 invites chahiye.\nAbhi aapke invites: {user['invites']}")
        else:
             bot.reply_to(message, "✅ Request Submitted! (Fake)")

@server.route('/')
def home():
    return "Bot Running Securely!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
