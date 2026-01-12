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

# ⚠️ YAHAN APNA MONETAG DIRECT LINK DALNA (Zaroori hai)
# Monetag Dashboard -> Sites -> Create Direct Link -> Copy URL
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

# --- 1. MONETAG OPTIMIZED PLAYER ---
@server.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    if not user_id: return "Error"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Video Ad</title>
        <style>
            body {{ background-color: #000; color: white; font-family: Arial, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; overflow: hidden; }}
            
            /* PLAYER CONTAINER */
            .video-box {{
                position: relative; width: 100%; max-width: 450px; aspect-ratio: 16/9;
                background: #111; border-radius: 0; 
                background-image: url('https://img.freepik.com/free-vector/video-player-template_23-2148524458.jpg');
                background-size: cover; background-position: center;
                box-shadow: 0 4px 20px rgba(0,0,0,0.8);
            }}

            /* INVISIBLE MONETAG TRIGGER (Poore screen pe link) */
            .ad-trigger {{
                position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                z-index: 999; cursor: pointer;
            }}

            /* PLAY ICON */
            .play-icon {{
                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                width: 70px; height: 70px;
                background: rgba(0,0,0,0.6); border-radius: 50%; border: 3px solid #4CAF50;
                display: flex; align-items: center; justify-content: center;
                font-size: 30px; color: #4CAF50;
                box-shadow: 0 0 15px #4CAF50;
            }}
            .play-icon::after {{ content: '▶'; margin-left: 5px; }}

            /* LOADING BAR */
            .loading-bar {{
                position: absolute; bottom: 0; left: 0; height: 5px; width: 0%;
                background: #4CAF50; transition: width 0.1s linear;
            }}

            .status {{ margin-top: 20px; font-size: 16px; color: #aaa; text-align: center; }}
        </style>
    </head>
    <body>

        <div class="video-box">
            <a href="{AD_LINK}" target="_blank" class="ad-trigger" onclick="runScript(this)"></a>
            
            <div class="play-icon" id="btn"></div>
            <div class="loading-bar" id="bar"></div>
        </div>

        <div class="status" id="txt">Tap Play to Watch Ad</div>

        <script>
            // Is Link par wapas aana hai
            let verifyUrl = "{SITE_URL}/verify?user_id={user_id}";

            function runScript(link) {{
                // 1. UI Changes
                document.getElementById('btn').style.display = 'none';
                document.getElementById('txt').innerText = "Verifying Ad View...";
                document.getElementById('txt').style.color = "#4CAF50";
                
                // Link ko disable karo taaki double click na ho
                link.style.pointerEvents = "none";

                // 2. Timer (10 Seconds is enough for Monetag)
                let width = 0;
                let bar = document.getElementById('bar');
                
                let timer = setInterval(() => {{
                    width += 1;
                    bar.style.width = width + '%';
                    
                    if(width >= 100) {{
                        clearInterval(timer);
                        document.getElementById('txt').innerText = "Success! Redirecting...";
                        
                        // 3. AUTO REDIRECT TO TELEGRAM
                        window.location.href = verifyUrl;
                    }}
                }}, 100); // 10 Sec total
            }}
        </script>
    </body>
    </html>
    """
    return html

# --- 2. VERIFY ROUTE (Deep Link) ---
@server.route('/verify')
def verify_task():
    try:
        user_id = request.args.get('user_id')
        uid = int(user_id)
        
        amount = round(random.uniform(3.00, 5.00), 2)
        inc_balance(uid, amount)
        inc_ads(uid)
        
        # Open Telegram App
        return redirect(f"tg://resolve?domain={BOT_USERNAME}&start=verified_{amount}")
    except:
        return "Error"

# --- BOT COMMANDS ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if len(message.text.split()) > 1 and message.text.split()[1].startswith("verified_"):
        amt = message.text.split("_")[1]
        bot.reply_to(message, f"✅ **Bonus Added!**\n💰 +₹{amt}", reply_markup=main_menu())
        return
    
    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ Join Channel First!", reply_markup=force_sub_markup())
        return

    get_user(user_id, message.from_user.username)
    bot.reply_to(message, f"👋 Namaste {message.from_user.first_name}!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🎬 Watch & Earn 🤑")
def watch_ad(message):
    if not SITE_URL: 
        bot.reply_to(message, "❌ Admin Error: SITE_URL not set")
        return
    
    user_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Watch Video", web_app=web_app))
    
    bot.reply_to(message, "👇 **Click Play & Wait:**", reply_markup=markup)

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
    return "✅ MoneyTube v8.0 (Monetag Edition) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
