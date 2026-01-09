import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
import time
import random
import uuid
from datetime import datetime, date, timedelta
# URL encode ke liye zaroori library
from urllib.parse import quote 

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")
ADMIN_ID = os.environ.get("ADMIN_ID")
AD_LINK = os.environ.get("AD_LINK", "https://google.com")
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
    markup.row(types.KeyboardButton("🚀 Start Earning (Ads)"))
    markup.add(types.KeyboardButton("💰 My Wallet"), types.KeyboardButton("👥 Refer & Earn"))
    markup.add(types.KeyboardButton("🎁 Daily Check-in"), types.KeyboardButton("📊 Live Proofs"))
    markup.add(types.KeyboardButton("🏦 Withdraw Money"), types.KeyboardButton("🆘 Support"))
    return markup

def withdraw_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer", "🔙 Main Menu")
    return markup

# --- ADMIN PANEL ---
@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    
    total_users = len(user_data)
    total_bal = sum(u['balance'] for u in user_data.values())
    total_ads = sum(u['ads_watched'] for u in user_data.values())
    
    bot.reply_to(message, f"👮‍♂️ **Admin Report**\n\n👥 Users: {total_users}\n💰 Distributed: ₹{round(total_bal, 2)}\n📺 Ads: {total_ads}")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    msg = message.text.replace('/broadcast', '').strip()
    if not msg:
        bot.reply_to(message, "⚠️ Message likho. Example: `/broadcast Hello`")
        return
    count = 0
    for uid in user_data:
        try:
            bot.send_message(uid, f"📢 **Alert:**\n\n{msg}")
            count += 1
        except: pass
    bot.reply_to(message, f"✅ Sent to {count} users.")

# --- MAIN LOGIC ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    
    if user_id not in user_data:
        is_new = True
        if ADMIN_ID:
            try: bot.send_message(ADMIN_ID, f"🔔 New User: {first_name} (ID: `{user_id}`)")
            except: pass
    else:
        is_new = False
        
    user = get_user(user_id)
    user['username'] = message.from_user.username

    args = message.text.split()
    if len(args) > 1:
        payload = args[1]
        
        if payload == user.get('pending_token'):
            amount = round(random.uniform(4.50, 6.50), 2)
            user['balance'] += amount
            user['ads_watched'] += 1
            user['pending_token'] = None
            bot.reply_to(message, f"✅ **Task Verified!**\n\n💵 **+₹{amount}** Added!\n💼 Balance: ₹{round(user['balance'], 2)}")
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

    welcome_msg = (f"👋 Namaste **{first_name}**!\n\n💎 **CashFlow Prime** mein swagat hai.\n👇 Start Earning:")
    bot.reply_to(message, welcome_msg, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Start Earning (Ads)")
def earn_money(message):
    user_id = message.chat.id
    user = get_user(user_id)
    token = str(uuid.uuid4())[:8]
    user['pending_token'] = token
    
    final_dest = f"https://t.me/{BOT_USERNAME}?start={token}"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👉 Watch Ad & Earn", url=final_dest))
    
    bot.reply_to(message, "📺 **New Task**\n\nLink par click karein aur wapas aate hi paise payein!", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.chat.id
    text = message.text
    user = get_user(user_id)
    
    if text == "💰 My Wallet":
        bot.reply_to(message, f"💳 **Wallet**\n💰: ₹{round(user['balance'], 2)}\n📺 Ads: {user['ads_watched']}\n👥 Refers: {user['invites']}")
    
    # --- YAHAN HUA HAI MAGIC CHANGE ---
    elif text == "👥 Refer & Earn":
        # 1. Apna Referral Link banao
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        
        # 2. Wo message jo user share karega (Encode karna zaroori hai)
        share_text = f"🔥 Bhai ye bot check kar! Maine isse paise kamaye hain.\n\n👇 Tu bhi join kar:\n{ref_link}"
        encoded_text = quote(share_text)
        
        # 3. Share URL banao
        share_url = f"https://t.me/share/url?url={ref_link}&text={encoded_text}"
        
        # 4. Button Banao
        markup = types.InlineKeyboardMarkup()
        # Ye button dabane par Forward Menu khulega
        btn_share = types.InlineKeyboardButton("🚀 Doston Ko Invite Bhejo", url=share_url)
        markup.add(btn_share)
        
        bot.reply_to(message, f"🤝 **Refer & Earn Program**\n\nShare karein aur har friend par **₹40** kamayein!\n\n🔗 **Your Link:**\n`{ref_link}`\n\n👇 Niche button dabakar direct share karein:", reply_markup=markup, parse_mode="Markdown")
    
    elif text == "🎁 Daily Check-in":
        today = str(date.today())
        if user['last_bonus'] == today:
            bot.reply_to(message, "⏳ **Wait!** Bonus already claimed.")
        else:
            bonus = round(random.uniform(5.00, 10.00), 2)
            user['balance'] += bonus
            user['last_bonus'] = today
            bot.reply_to(message, f"🎉 **Bonus!** +₹{bonus} Added!")
            
    elif text == "📊 Live Proofs":
        bot.reply_to(message, "🟢 **Recent Payouts:**\nUser88: ₹500 ✅")
        
    elif text == "🏦 Withdraw Money":
        bot.reply_to(message, "🏧 Select Method:", reply_markup=withdraw_menu())
        
    elif text == "🆘 Support":
        bot.reply_to(message, f"📞 Contact Admin: @{SUPPORT_USER}")
        
    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 Home", reply_markup=main_menu())
        
    elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
         bot.reply_to(message, "✅ Request Submitted (Processing...)")

@server.route('/')
def home():
    return "Bot Updated with Share Button!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
