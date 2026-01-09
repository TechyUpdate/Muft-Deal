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
# Apne Bot ka username yahan likho (Bina @ ke) - Zaroori hai redirect ke liye!
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MoneyTubeBot") 
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Admin")

# --- SHORTENER SETTING (IMPORTANT) ---
# Yahan apna Link Shortener ka URL format dalo.
# %s ki jagah humara secret code aayega.
# Example: "https://gplinks.in/api?api=YOUR_KEY&url=https://t.me/MYBOT?start=%s"
# Testing ke liye hum seedha telegram link use kar rahe hain:
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
            'pending_token': None # Secret code save karne ke liye
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

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    user = get_user(user_id)
    
    # --- MAGIC VERIFICATION LOGIC ---
    # Jab user Link se wapas aayega: /start TOKEN_CODE
    args = message.text.split()
    
    if len(args) > 1:
        payload = args[1]
        
        # 1. Check karo kya ye AD VERIFICATION wala code hai?
        if payload == user.get('pending_token'):
            # Paisa add karo!
            amount = round(random.uniform(4.50, 6.50), 2)
            user['balance'] += amount
            user['ads_watched'] += 1
            user['pending_token'] = None # Token delete kar do (Reuse na ho)
            
            bot.reply_to(message, f"✅ **Task Completed!**\n\nSystem ne verify kar liya hai ki aapne Ad dekha.\n💵 **+₹{amount}** Added!\n💼 New Balance: ₹{round(user['balance'], 2)}")
            return # Yahi ruk jao, welcome message mat bhejo

        # 2. Check Referral (Agar ad code nahi hai to referral hoga)
        elif payload.isdigit() and int(payload) != user_id:
            referrer_id = int(payload)
            if user['joined_via'] is None:
                user['joined_via'] = referrer_id
                # Referrer logic here...

    welcome_msg = (f"👋 Namaste **{first_name}**!\n\n"
                   f"💎 **CashFlow Prime** mein swagat hai.\n"
                   f"India ka sabse bharosemand Earning App.\n\n"
                   f"👇 Niche diye button se kamai shuru karein:")
    bot.reply_to(message, welcome_msg, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Start Earning (Ads)")
def earn_money(message):
    user_id = message.chat.id
    user = get_user(user_id)
    
    # 1. Ek Naya Secret Token Banao
    secret_token = str(uuid.uuid4())[:8] # e.g., "a1b2c3d4"
    user['pending_token'] = secret_token # Database mein save kar lo
    
    # 2. Link Banao (Redirect wala)
    # Agar tumhare paas Shortener hai, to user wahan jayega, fir wapas aayega
    # Final link aisa banega: https://t.me/BotName?start=a1b2c3d4
    
    # REPLACE THIS LOGIC WITH YOUR SHORTENER LATER
    # Abhi ke liye hum dummy link bana rahe hain
    final_link = f"https://t.me/{BOT_USERNAME}?start={secret_token}"
    
    # Agar tumhare paas Link Shortener API hai, to yahan wo link aayega
    # Example: link_to_send = f"https://gplinks.in/shorten?url={final_link}"
    
    msg = (f"📺 **New Ad Available**\n\n"
           f"1. Link par click karein.\n"
           f"2. Ad website par redirect hoga.\n"
           f"3. Jaise hi task pura hoga, aap automatically bot par wapas aayenge aur paise mil jayenge.\n\n"
           f"👇 **Click to Watch:**")
    
    markup = types.InlineKeyboardMarkup()
    # Note: Asli setup mein ye link shortener ka hoga
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
             # Timer Logic
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            midnight = datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, hour=0, minute=0, second=0)
            remaining = midnight - now
            seconds = remaining.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
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
        
    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 Home", reply_markup=main_menu())

@server.route('/')
def home():
    return "Bot Running with Deep Linking!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
