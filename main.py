import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os

# --- SETUP (SECURE) ---
# Ye line ab Render ke "Environment Variable" se token uthayegi
TOKEN = os.environ.get("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# --- FAKE DATABASE (Temporary) ---
user_data = {}

def get_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {'balance': 0, 'invites': 0}
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
    get_user(user_id) 
    
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
        # Note: Agar bot crash ho to ensure karna ki username sahi se fetch ho raha hai
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        msg = (f"📣 **MoneyTube Refer & Earn**\n\n"
               f"Apne doston ko invite karein aur payein ₹50 har invite par!\n\n"
               f"👇 Aapka Referral Link:\n{ref_link}")
        bot.reply_to(message, msg)

    # 3. DAILY BONUS
    elif "Bonus" in text:
        user['balance'] += 10
        bot.reply_to(message, "🎉 Badhai ho! MoneyTube ki taraf se ₹10 ka Daily Bonus mila hai.")

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
    return "MoneyTube Bot is running secure!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
