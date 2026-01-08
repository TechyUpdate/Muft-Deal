import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
import time
from datetime import date

# --- SETUP ---
TOKEN = os.environ.get("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# --- MEMORY DATABASE ---
# Note: Render restart hone par ye data ud jayega. 
# Permanent data ke liye MongoDB lagana padta hai (jo thoda advanced hai).
user_data = {}

def get_user(user_id):
    if user_id not in user_data:
        # Default data set karo
        user_data[user_id] = {
            'balance': 0, 
            'invites': 0,
            'last_bonus': None, # Bonus track karne ke liye
            'joined_via': None  # Kisne invite kiya
        }
    return user_data[user_id]

# --- KEYBOARD MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("💰 Available Balance")
    btn2 = types.KeyboardButton("👫 Invite Friends")
    btn3 = types.KeyboardButton("💸 Withdraw Funds")
    btn4 = types.KeyboardButton("🎁 Daily Bonus")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

def withdraw_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("💥 UPI")
    btn2 = types.KeyboardButton("💙 Paytm")
    btn3 = types.KeyboardButton("📱 PhonePe")
    btn4 = types.KeyboardButton("🔙 Main Menu")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# --- BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    
    # Check karein ki user naya hai ya purana
    is_new_user = user_id not in user_data
    
    # User ko database mein lao
    user = get_user(user_id) 
    
    # --- REFERRAL SYSTEM LOGIC ---
    # Command ke saath jo text aata hai (jaise /start 12345)
    args = message.text.split()
    
    if is_new_user and len(args) > 1:
        try:
            referrer_id = int(args[1])
            
            # Khud ko invite karne se roko
            if referrer_id != user_id:
                # Agar referrer exist karta hai
                if referrer_id in user_data:
                    # 1. New user ka record update karo
                    user['joined_via'] = referrer_id
                    
                    # 2. Referrer ko reward do
                    user_data[referrer_id]['balance'] += 50
                    user_data[referrer_id]['invites'] += 1
                    
                    # 3. Referrer ko NOTIFICATION bhejo (Jo pehle missing tha)
                    try:
                        bot.send_message(
                            referrer_id, 
                            f"🚀 **Naya Referral!**\n\n"
                            f"Badhai ho! {first_name} ne aapke link se join kiya hai.\n"
                            f"✅ Aapke wallet mein ₹50 add kar diye gaye hain.\n"
                            f"👥 Total Invites: {user_data[referrer_id]['invites']}"
                        )
                    except:
                        pass # Agar referrer ne bot block kiya ho to ignore karo
        except ValueError:
            pass

    welcome_text = (f"Namaste {first_name}! 👋\n\n"
                    "Swagat hai **MoneyTube** Bot par! 💰\n"
                    "Yahan videos dekho, friends ko invite karo aur paise kamao.\n\n"
                    "👇 Niche diye gaye buttons use karein:")
    
    bot.reply_to(message, welcome_text, reply_markup=main_menu())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.chat.id
    text = message.text
    user = get_user(user_id)

    # 1. BALANCE CHECK
    if "Balance" in text:
        bal = user['balance']
        invites = user['invites']
        bot.reply_to(message, f"🏦 **MoneyTube Wallet**\n\n💰 Balance: ₹{bal}\n👥 Total Invites: {invites}", parse_mode="Markdown")

    # 2. INVITE LINK
    elif "Invite" in text:
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        msg = (f"📣 **MoneyTube Refer & Earn**\n\n"
               f"Apne doston ko invite karein aur payein ₹50 har invite par!\n\n"
               f"👇 Aapka Referral Link:\n{ref_link}")
        bot.reply_to(message, msg)

    # 3. DAILY BONUS (FIXED LOGIC)
    elif "Bonus" in text:
        today = str(date.today()) # Aaj ki date (e.g., '2023-10-25')
        
        if user['last_bonus'] == today:
            # Agar aaj ka bonus le chuka hai
            bot.reply_to(message, "❌ **Oops!**\n\nAap aaj ka bonus le chuke hain.\nKripya kal wapas aana! ⏳")
        else:
            # Agar nahi liya
            user['balance'] += 10
            user['last_bonus'] = today # Date save kar lo
            bot.reply_to(message, "🎉 **Bonus Claimed!**\n\nAapko aaj ka ₹10 bonus mil gaya hai.\nKal fir aana! ✅")

    # 4. WITHDRAW
    elif "Withdraw" in text:
        bot.reply_to(message, "👇 Withdrawal method select karein:", reply_markup=withdraw_menu())

    # 5. PAYMENT METHODS
    elif text in ["💥 UPI", "💙 Paytm", "📱 PhonePe"]:
        if user['invites'] < 5:
            remaining = 5 - user['invites']
            error_msg = (f"⚠️ **Withdrawal Locked!**\n\n"
                         f"MoneyTube se paise nikalne ke liye kam se kam 5 doston ko invite karna zaroori hai.\n\n"
                         f"❌ Abhi aapke invites: {user['invites']}\n"
                         f"⏳ Aur chahiye: {remaining}")
            bot.reply_to(message, error_msg)
        else:
            bot.reply_to(message, "✅ Request le li gayi hai! (Processing...)")

    elif "Main Menu" in text:
        bot.reply_to(message, "🏠 Main Menu par wapas aa gaye.", reply_markup=main_menu())

# --- SERVER KEEPER ---
@server.route('/')
def home():
    return "MoneyTube Bot is running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
