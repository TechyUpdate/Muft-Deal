import telebot
from telebot import types
from flask import Flask, request, redirect
from threading import Thread
import os
import random
from datetime import date
import pymongo
import certifi

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MoneyTubeBot").replace("@", "")

# TERA MONETAG DIRECT LINK (Yahan daal dena)
AD_LINK = os.environ.get("AD_LINK", "https://google.com") 

SITE_URL = os.environ.get("SITE_URL", "") 
SUPPORT_USER = os.environ.get("SUPPORT_USER", "Admin")

MONGO_URI = os.environ.get("MONGO_URI", "")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "") 

# --- DATABASE ---
if not MONGO_URI:
    db = None
else:
    try:
        client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client['moneytube_db']
        users_col = db['users']
    except:
        db = None

bot = telebot.TeleBot(TOKEN) if TOKEN else None
server = Flask(__name__)

# --- HELPERS ---
def get_user(user_id, username=None):
    if db is None: return {} 
    user = users_col.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id, "balance": 0.0, "invites": 0, "ads_watched": 0, "withdraw_count": 0,
            "joined_via": None, "last_bonus": None, "username": username, "joined_date": str(date.today())
        }
        users_col.insert_one(user)
    return user

def update_user(user_id, data):
    if db is not None: users_col.update_one({"_id": user_id}, {"$set": data})

def inc_balance(user_id, amount):
    if db is not None: users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})

def inc_ads(user_id):
    if db is not None: users_col.update_one({"_id": user_id}, {"$inc": {"ads_watched": 1}})

def inc_invites(user_id):
    if db is not None: users_col.update_one({"_id": user_id}, {"$inc": {"invites": 1}})

def inc_withdraw_count(user_id):
    if db is not None: users_col.update_one({"_id": user_id}, {"$inc": {"withdraw_count": 1}})

def is_user_member(user_id):
    if not CHANNEL_USERNAME: return True 
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['creator', 'administrator', 'member']
    except: return True 

# --- 1. DIRECT INVISIBLE REDIRECT PAGE ---
@server.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    if not user_id: return "Error"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Loading...</title>
        <style>
            body {{ background-color: #000; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; font-family: Arial, sans-serif; }}
            
            /* LOADER (Sirf ye dikhega jab tak Ad nahi khulta) */
            .loader {{
                border: 4px solid #333;
                border-top: 4px solid #4CAF50;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 0.8s linear infinite;
                margin-bottom: 20px;
            }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            
            p {{ color: #888; font-size: 14px; }}
            
            /* Invisible Click Layer (Backup ke liye) */
            .tap-layer {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10; }}
        </style>
    </head>
    <body>

        <div class="loader"></div>
        <p>Please wait...</p>
        
        <div class="tap-layer" onclick="goNow()"></div>

        <script>
            let adLink = "{AD_LINK}";
            let verifyLink = "{SITE_URL}/verify?user_id={user_id}";

            function goNow() {{
                // 1. Mark as Visited
                sessionStorage.setItem("visited", "true");
                
                // 2. Redirect to Ad (Same Tab)
                window.location.href = adLink;
            }}

            // 3. AUTO RUN ON LOAD
            window.onload = function() {{
                // Check agar user wapas aaya hai (Back button dabake)
                if(sessionStorage.getItem("visited") === "true") {{
                    sessionStorage.removeItem("visited");
                    document.body.innerHTML = "<h2 style='color:#4CAF50; text-align:center;'>✅ Done!</h2>";
                    // Send to Telegram
                    window.location.href = verifyLink;
                }} else {{
                    // Pehli baar aaya hai -> Go to Ad immediately
                    setTimeout(goNow, 500); // 0.5 sec delay taaki browser block na kare
                }}
            }};
        </script>
    </body>
    </html>
    """
    return html

# --- 2. VERIFY ROUTE ---
@server.route('/verify')
def verify_task():
    try:
        user_id = request.args.get('user_id')
        uid = int(user_id)
        
        amount = round(random.uniform(4.00, 8.00), 2)
        inc_balance(uid, amount)
        inc_ads(uid)
        
        return redirect(f"tg://resolve?domain={BOT_USERNAME}&start=verified_{amount}")
    except:
        return "Error"

# --- BOT COMMANDS (SAME) ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if len(message.text.split()) > 1 and message.text.split()[1].startswith("verified_"):
        amt = message.text.split("_")[1]
        bot.reply_to(message, f"✅ **Bonus Received!**\n💰 **+₹{amt}**", reply_markup=main_menu())
        return

    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ Join Channel First", reply_markup=force_sub_markup())
        return
    
    get_user(user_id, message.from_user.username)
    bot.reply_to(message, "👋 Welcome!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🎬 Watch & Earn 🤑")
def watch_ad(message):
    if not SITE_URL: 
        bot.reply_to(message, "❌ Error: SITE_URL missing")
        return
    
    user_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Watch Video", web_app=web_app))
    
    bot.reply_to(message, "👇 **Wait... Ad Loading:**", reply_markup=markup)

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🎬 Watch & Earn 🤑")
    markup.row("💼 My Account", "💸 Paisa Nikalo")
    markup.row("🎁 Daily Bonus", "🚀 Share & Loot")
    markup.row("👤 VIP Profile", "⚙️ Settings")
    return markup

def force_sub_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Check Joined", callback_data="check_join"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_join(call):
    if is_user_member(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "🏠 **Main Menu**", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ Not Joined Yet!", show_alert=True)

# --- SERVER ---
@server.route('/')
def home():
    return "✅ MoneyTube v13.0 (Direct - No Player) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
