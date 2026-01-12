import telebot
from telebot import types
from flask import Flask, request, redirect
from threading import Thread
import os
import time
import random
import uuid
from datetime import datetime, date, timedelta
import pymongo
import certifi

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MoneyTubeBot").replace("@", "")

# YAHAN APNA ADSTERRA DIRECT LINK DALNA (Jo prime-win pe le jata hai)
AD_LINK = os.environ.get("AD_LINK", "https://your-adsterra-link.com") 

# TERA RENDER LINK (Bina slash ke last me)
SITE_URL = os.environ.get("SITE_URL", "") 
SUPPORT_USER = os.environ.get("SUPPORT_USER", "Admin")

MONGO_URI = os.environ.get("MONGO_URI", "")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "") 

# --- DATABASE CONNECTION ---
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
            "joined_via": None, "username": username, "joined_date": str(date.today())
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

# --- 1. THE FAKE PLAYER PAGE (Ye hai DhanTube ka Raaz) ---
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
        <title>Video Player</title>
        <style>
            body {{
                margin: 0; padding: 0;
                background-color: #0d0d0d;
                color: white;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                height: 100vh;
            }}
            .header {{
                position: absolute; top: 20px;
                font-size: 18px; font-weight: 600;
                color: #fff;
                display: flex; align-items: center; gap: 5px;
            }}
            .money-icon {{ color: #4caf50; }}
            
            /* PLAYER BOX */
            .player-container {{
                width: 90%; max-width: 400px;
                aspect-ratio: 16/9;
                background-color: #000;
                border-radius: 12px;
                position: relative;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                border: 1px solid #333;
                background-image: url('https://img.freepik.com/free-vector/video-player-template_23-2148524458.jpg');
                background-size: cover;
                cursor: pointer;
            }}
            
            /* PLAY BUTTON */
            .play-overlay {{
                position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.4);
                display: flex; align-items: center; justify-content: center;
                z-index: 2;
            }}
            .play-icon {{
                width: 60px; height: 60px;
                background: rgba(255,255,255,0.9);
                border-radius: 50%;
                display: flex; align-items: center; justify-content: center;
                box-shadow: 0 0 20px rgba(255,255,255,0.3);
                transition: transform 0.2s;
            }}
            .play-icon::after {{
                content: '';
                border-style: solid;
                border-width: 10px 0 10px 18px;
                border-color: transparent transparent transparent #000;
                margin-left: 4px;
            }}
            .player-container:active .play-icon {{ transform: scale(0.9); }}

            /* LOADING BAR (LINING) */
            .loading-container {{
                width: 90%; max-width: 400px;
                margin-top: 20px;
                display: none; /* Initially Hidden */
            }}
            .progress-track {{
                width: 100%; height: 4px;
                background: #333;
                border-radius: 2px;
                overflow: hidden;
            }}
            .progress-bar {{
                width: 0%; height: 100%;
                background: #2196f3; /* BLUE COLOR (DhanTube Style) */
                border-radius: 2px;
                transition: width 0.1s linear;
            }}
            .status-text {{
                margin-top: 10px;
                font-size: 14px; color: #aaa;
                text-align: center;
            }}

            /* FULL SCREEN CLICK JACKER */
            .click-layer {{
                position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                z-index: 10; cursor: pointer;
            }}
        </style>
    </head>
    <body>

        <div class="header">
            <span class="money-icon">💰</span> Watch Video
        </div>

        <div class="player-container">
            <div class="play-overlay" id="playBtn">
                <div class="play-icon"></div>
            </div>
            <div class="click-layer" onclick="handleAdClick()"></div>
        </div>

        <div class="loading-container" id="loader">
            <div class="progress-track">
                <div class="progress-bar" id="bar"></div>
            </div>
            <div class="status-text" id="status">Please wait...</div>
        </div>

        <script>
            let adLink = "{AD_LINK}";
            let verifyLink = "{SITE_URL}/verify?user_id={user_id}";
            let clicked = false;

            function handleAdClick() {{
                if(clicked) return;
                clicked = true;

                // 1. OPEN ADSTERRA (Prime-Win)
                window.open(adLink, "_blank");

                // 2. UI CHANGE (DhanTube Style)
                document.getElementById('playBtn').style.display = 'none'; // Hide Play Button
                document.getElementById('loader').style.display = 'block'; // Show Blue Line

                // 3. START TIMER (15 Seconds)
                let width = 0;
                let bar = document.getElementById('bar');
                let status = document.getElementById('status');
                
                let interval = setInterval(() => {{
                    width += 0.66; // Slower speed for 15s
                    bar.style.width = width + '%';
                    
                    if(width >= 100) {{
                        clearInterval(interval);
                        status.innerText = "Redirecting...";
                        status.style.color = "#4caf50";
                        
                        // 4. AUTO REDIRECT (No Button)
                        window.location.href = verifyLink;
                    }}
                }}, 100);
            }}
        </script>
    </body>
    </html>
    """
    return html

# --- 2. VERIFY ROUTE (Automatic App Open) ---
@server.route('/verify')
def verify_task():
    try:
        user_id = request.args.get('user_id')
        uid = int(user_id)
        
        # Paise Add
        amount = round(random.uniform(3.00, 6.00), 2)
        inc_balance(uid, amount)
        inc_ads(uid)
        
        # Deep Link Redirect (Telegram App me wapas)
        return redirect(f"tg://resolve?domain={BOT_USERNAME}&start=verified_{amount}")
    except:
        return "Error"

# --- BOT HANDLERS (Standard) ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if len(message.text.split()) > 1 and message.text.split()[1].startswith("verified_"):
        amt = message.text.split("_")[1]
        bot.reply_to(message, f"✅ **Bonus Received!**\n💰 Added: ₹{amt}", reply_markup=main_menu())
        return
    
    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ Join Channel First!", reply_markup=force_sub_markup())
        return

    get_user(user_id, message.from_user.username)
    bot.reply_to(message, "👋 Welcome!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🎬 Watch & Earn 🤑")
def watch_ad(message):
    if not SITE_URL: 
        bot.reply_to(message, "❌ Setup Error: SITE_URL missing")
        return
    
    user_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    # WebApp Button (Telegram ke andar khulne ke liye)
    web_app = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Watch Video", web_app=web_app))
    
    bot.reply_to(message, "👇 **Click Play & Wait 15s:**", reply_markup=markup)

# --- MENUS (SAME) ---
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
    return "✅ MoneyTube v5.0 (Clone Script) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
