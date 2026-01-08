import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
import time
import random
from datetime import datetime, date

# --- CONFIGURATION (SECURE) ---
# Ye sab ab Render ke "Environment Variables" se aayega
TOKEN = os.environ.get("BOT_TOKEN")

# Agar Render me link nahi dala to Google khulega (Safety ke liye)
AD_LINK = os.environ.get("AD_LINK", "https://www.google.com") 
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Admin")

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
            'joined_date': str(date.today()),
            'last_bonus': None,
            'joined_via': None,
            'status': 'Bronze Member 🥉'
        }
    return user_data[user_id]

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_earn = types.KeyboardButton("🚀 Start Earning (Ads)")
    markup.row(btn_earn)
    btn1 = types.KeyboardButton("💰 My Wallet")
    btn2 = types.KeyboardButton("👥 Refer & Earn")
    markup.add(btn1, btn2)
    btn3 = types.KeyboardButton("🎁 Daily Check-in")
    btn4 = types.KeyboardButton("📊 Live Proofs")
    markup.add(btn3, btn4)
    btn5 = types.KeyboardButton("🏦 Withdraw Money")
    btn6 = types.KeyboardButton("🆘 Support")
    markup.add(btn5, btn6)
    return markup

def ad_verify_menu():
    markup = types.InlineKeyboardMarkup()
    # Yahan wo variable wala link use hoga
    btn_link = types.InlineKeyboardButton("👉 Click Here to Watch Ad", url=AD_LINK)
    btn_verify = types.InlineKeyboardButton("✅ Maine Ad Dekh Liya", callback_data="verify_ad")
    markup.add(btn_link)
    markup.add(btn_verify)
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
    is_new = user_id not in user_data
    user = get_user(user_id)
    
    args = message.text.split()
    if is_new and len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id != user_id and referrer_id in user_data:
                user['joined_via'] = referrer_id
                user_data[referrer_id]['balance'] += 40.0
                user_data[referrer_id]['invites'] += 1
                invites = user_data[referrer_id]['invites']
                if invites > 10: user_data[referrer_id]['status'] = 'Silver Member 🥈'
                if invites > 50: user_data[referrer_id]['status'] = 'Gold Member 🥇'
                try:
                    bot.send_message(referrer_id, f"🌟 **Premium Referral!**\n\nEk naya member juda hai!\n💵 **+₹40.00** added.")
                except: pass
        except: pass

    welcome_msg = (f"👋 Namaste **{first_name}**!\n\n"
                   f"💎 **CashFlow Prime** mein swagat hai.\n"
                   f"India ka sabse bharosemand Earning App ab Telegram par!\n\n"
                   f"🏆 **Aapka Status:** {user['status']}\n\n"
                   f"👇 Niche diye button se kamai shuru karein:")
    bot.reply_to(message, welcome_msg, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🚀 Start Earning (Ads)")
def earn_money(message):
    msg = (f"📺 **Premium Ad Task**\n\n"
           f"1. Niche button par click karein.\n"
           f"2. Website par **10 second** rukna zaroori hai.\n"
           f"3. Wapas aakar 'Verify' dabayein.\n\n"
           f"⚠️ **Warning:** Agar ad pura nahi dekha to paise nahi milenge.")
    bot.reply_to(message, msg, reply_markup=ad_verify_menu())

@bot.callback_query_handler(func=lambda call: call.data == "verify_ad")
def verify_ad_click(call):
    user_id = call.message.chat.id
    user = get_user(user_id)
    bot.answer_callback_query(call.id, "Checking server status... ⏳")
    time.sleep(1)
    amount = round(random.uniform(4.50, 6.50), 2)
    user['balance'] += amount
    user['ads_watched'] += 1
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                          text=f"✅ **Task Verified!**\n\n💵 Amount: ₹{amount}\n💼 Total Balance: ₹{round(user['balance'], 2)}\n\nAgla ad dekhne ke liye 'Start Earning' dabayein!")

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.chat.id
    text = message.text
    user = get_user(user_id)
    
    if text == "💰 My Wallet":
        bal = round(user['balance'], 2)
        bot.reply_to(message, f"💳 **Wallet Dashboard**\n\n💰 **Balance:** ₹{bal}\n🏅 **Status:** {user['status']}\n📺 **Ads Watched:** {user['ads_watched']}")

    elif text == "👥 Refer & Earn":
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.reply_to(message, f"🤝 **Partner Program**\n\nInvite karein aur kamaein:\n✅ **₹40** per Refer\n✅ **10%** Lifetime Commission\n\n🔗 **Aapka VIP Link:**\n{link}")

    elif text == "🎁 Daily Check-in":
        today = str(date.today())
        if user['last_bonus'] == today:
            bot.reply_to(message, "⏳ **Wait!** Aap aaj ka bonus le chuke hain.")
        else:
            bonus = round(random.uniform(5.00, 10.00), 2)
            user['balance'] += bonus
            user['last_bonus'] = today
            bot.reply_to(message, f"🎉 **Daily Bonus!**\n\nAapko mile hain **₹{bonus}** free mein!\nKal fir aana.")

    elif text == "📊 Live Proofs":
        proofs = (f"🟢 **Recent Payouts (Last Hour)**\n\n"
                  f"1. Rahul K. - ₹520 (Paytm) ✅\n"
                  f"2. Priya S. - ₹850 (UPI) ✅\n"
                  f"3. Amit99 - ₹400 (PhonePe) ✅\n"
                  f"4. User77 - ₹1200 (Bank) ✅\n\n"
                  f"👇 Apna number lagane ke liye kaam karte rahein!")
        bot.reply_to(message, proofs)

    elif text == "🏦 Withdraw Money":
        bot.reply_to(message, "🏧 **Withdrawal Gateway**\n\nSelect Payment Method:", reply_markup=withdraw_menu())
        
    elif text == "🆘 Support":
        # Yahan variable wala username dikhega
        bot.reply_to(message, f"📞 **24/7 Support**\n\nAgar paise add nahi huye, to screenshot lekar Admin ko bhejein:\n@{ADMIN_USERNAME}")

    elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
        if user['invites'] < 10:
            remaining = 10 - user['invites']
            bot.reply_to(message, f"🔒 **Withdrawal Locked**\n\nAnti-Fraud system active hai.\nUnlock karne ke liye **{remaining} valid invites** aur chahiye.")
        else:
             bot.reply_to(message, "✅ Request Submitted!\n24-48 hours mein process hoga.")
             
    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 Home", reply_markup=main_menu())

@server.route('/')
def home():
    return "Premium Secure Bot Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
