import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
import time
import random
import uuid
from datetime import datetime, date, timedelta

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MoneyTubeBot")
# ADMIN_ID zaroori hai taaki bot tujhe pehchan sake (Ye numeric ID hoti hai)
ADMIN_ID = os.environ.get("ADMIN_ID") 

# Link Shortener Logic (Abhi Direct Link hai)
BASE_AD_LINK = os.environ.get("AD_LINK", f"https://t.me/{BOT_USERNAME}?start=%s")

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

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
            'username': None # Username save kar rahe hain tracking ke liye
        }
    return user_data[user_id]

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.row(types.KeyboardButton("🚀 Start Earning (Ads)"))
    markup.add(types.KeyboardButton("💰 My Wallet"), types.KeyboardButton("👥 Refer & Earn"))
    markup.add(types.KeyboardButton("🎁 Daily Check-in"), types.KeyboardButton("📊 Live Proofs"))
    markup.add(types.KeyboardButton("🏦 Withdraw Money"), types.KeyboardButton("🆘 Support"))
    return markup

def withdraw_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer", "🔙 Main Menu")
    return markup

# --- ADMIN PANEL (Only for You) ---

@bot.message_handler(commands=['admin', 'stats'])
def admin_stats(message):
    # Check karein ki message bhejne wala ADMIN hai ya koi aur
    if str(message.chat.id) != str(ADMIN_ID):
        return # Agar admin nahi hai to ignore karo

    total_users = len(user_data)
    total_ads = sum(user['ads_watched'] for user in user_data.values())
    total_balance = sum(user['balance'] for user in user_data.values())
    
    report = (f"👮‍♂️ **Admin Dashboard**\n\n"
              f"👥 **Total Users:** {total_users}\n"
              f"📺 **Total Ads Watched:** {total_ads}\n"
              f"💰 **Total User Balance:** ₹{round(total_balance, 2)}\n\n"
              f"System Mast chal raha hai! 🚀")
    
    bot.reply_to(message, report)

@bot.message_handler(commands=['broadcast'])
def broadcast_msg(message):
    # Sabhi users ko message bhejne ke liye: /broadcast Hello Dosto
    if str(message.chat.id) != str(ADMIN_ID):
        return

    msg = message.text.replace('/broadcast', '').strip()
    if not msg:
        bot.reply_to(message, "❌ Message to likho! Ex: `/broadcast Hello`")
        return

    sent_count = 0
    for uid in user_data:
        try:
            bot.send_message(uid, f"📢 **Announcement:**\n\n{msg}")
            sent_count += 1
        except:
            pass # Agar user ne block kiya hai to skip karo
    
    bot.reply_to(message, f"✅ Message sent to {sent_count} users.")

# --- USER HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    # Check New User
    if user_id not in user_data:
        is_new = True
    else:
        is_new = False
        
    user = get_user(user_id)
    user['username'] = username # Update username
    
    # --- ADMIN NOTIFICATION (Jadoo Yahan Hai) ---
    if is_new and ADMIN_ID:
        try:
            bot.send_message(
                ADMIN_ID,
                f"🔔 **New User Alert!**\n\n"
                f"👤 Name: {first_name}\n"
                f"🆔 ID: `{user_id}`\n"
                f"🔗 Username: @{username if username else 'No Username'}"
            )
        except:
            pass # Agar notification fail ho jaye to bot na ruke

    # --- MAGIC VERIFICATION LOGIC ---
    args = message.text.split()
    if len(args) > 1:
        payload = args[1]
        
        # 1. Ad Verification
        if payload == user.get('pending_token'):
            amount = round(random.uniform(4.50, 6.50), 2)
            user['balance'] += amount
            user['ads_watched'] += 1
            user['pending_token'] = None 
            
            bot.reply_to(message, f"✅ **Task Completed!**\n\nSystem Verified.\n💵 **+₹{amount}** Added!\n💼 Balance: ₹{round(user['balance'], 2)}")
            return 

        # 2. Referral Logic
        elif payload.isdigit() and int(payload) != user_id:
            referrer_id = int(payload)
            if user['joined_via'] is None:
                user['joined_via'] = referrer_id
                if referrer_id in user_data:
                    user_data[referrer_id]['balance'] += 40.0
                    user_data[referrer_id]['invites'] += 1
                    try:
                        bot.send_message(referrer_id, f"🌟 **Referral Bonus!**\n+₹40 Added (New Friend: {first_name})")
                    except: pass

    welcome_msg = (f"👋 Namaste **{first_name}**!\n\n"
                   f"💎 **CashFlow Prime** mein swagat hai.\n"
                   f"India ka sabse bharosemand Earning App.\n\n"
                   f"👇 Niche diye button se kamai shuru karein:")
    bot.reply_to(message, welcome_msg, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Start Earning (Ads)")
def earn_money(message):
    user_id = message.chat.id
    user = get_user(user_id)
    
    secret_token = str(uuid.uuid4())[:8]
    user['pending_token'] = secret_token 
    
    # Link Shortener Logic
    final_link = f"https://t.me/{BOT_USERNAME}?start={secret_token}"
    # Agar shortener API hai to yahan use karein
    
    msg = (f"📺 **New Ad Available**\n\n"
           f"1. Link par click karein.\n"
           f"2. Ad website par redirect hoga.\n"
           f"3. Task pura hote hi paise apne aap add ho jayenge.\n\n"
           f"👇 **Click to Watch:**")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👉 Watch Ad Now", url=final_link))
    
    bot.reply_to(message, msg, reply_markup=markup)

# --- STANDARD FEATURES ---
@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.chat.id
    text = message.text
    user = get_user(user_id)
    
    if text == "💰 My Wallet":
        bal = round(user['balance'], 2)
        bot.reply_to(message, f"💳 **Wallet Dashboard**\n\n💰 **Balance:** ₹{bal}\n🏅 **Status:** {user['status']}\n📺 **Ads Watched:** {user['ads_watched']}")

    elif text == "👥 Refer & Earn":
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        bot.reply_to(message, f"🔗 **Referral Link:**\n{link}")

    elif text == "🎁 Daily Check-in":
        today = str(date.today())
        if user['last_bonus'] == today:
            bot.reply_to(message, f"⏳ **Wait!** Next Bonus tomorrow.")
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
        bot.reply_to(message, f"📞 Support ke liye message karein.")

    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 Home", reply_markup=main_menu())

@server.route('/')
def home():
    return "Admin Enabled Bot Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
