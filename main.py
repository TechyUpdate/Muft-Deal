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

# --- 1. MONETAG SDK PAGE (Final Integrated) ---
@server.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    if not user_id: return "Error"
    
    # 🟢 TERA ASLI CODE YAHAN LAGA DIYA HAI
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Watch & Earn</title>
        
        <script src='//libtl.com/sdk.js' data-zone='10452164' data-sdk='show_10452164'></script>
        
        <style>
            body {{ background-color: #000; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; font-family: Arial, sans-serif; }}
            
            .video-box {{
                width: 90%; max-width: 400px; aspect-ratio: 16/9;
                background: #111 url('https://img.freepik.com/free-vector/video-player-template_23-2148524458.jpg') center/cover;
                border: 1px solid #333; border-radius: 10px; position: relative;
                display: flex; align-items: center; justify-content: center;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.2);
            }}
            
            .play-btn {{
                width: 70px; height: 70px; background: rgba(0,0,0,0.7); border-radius: 50%;
                display: flex; align-items: center; justify-content: center; font-size: 35px; cursor: pointer;
                border: 3px solid #4CAF50; color: #4CAF50; z-index: 10;
                animation: pulse 2s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7); }}
                70% {{ transform: scale(1.05); box-shadow: 0 0 0 10px rgba(76, 175, 80, 0); }}
                100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }}
            }}
            
            .status {{ margin-top: 20px; color: #aaa; font-size: 14px; }}
        </style>
    </head>
    <body>

        <h3 style="color: #4CAF50;">💰 Watch Video Ad</h3>

        <div class="video-box">
            <div class="play-btn" id="playBtn" onclick="showAd()">▶</div>
        </div>

        <div class="status" id="statusTxt">Tap Play to Earn Reward</div>

        <script>
            let verifyLink = "{SITE_URL}/verify?user_id={user_id}";

            function showAd() {{
                document.getElementById('statusTxt').innerText = "Loading Ad...";
                document.getElementById('playBtn').style.display = 'none'; // Button hata do
                
                // 2. TERA REWARD FUNCTION (Integrated)
                try {{
                    if (typeof show_10452164 === 'function') {{
                        show_10452164().then(() => {{
                            // Ad Khatam hote hi yahan aayega
                            document.getElementById('statusTxt').innerText = "✅ Success! Redirecting...";
                            window.location.href = verifyLink;
                        }});
                    }} else {{
                        alert("Ad load nahi ho raha. Refresh karein.");
                        window.location.reload();
                    }}
                }} catch (e) {{
                    console.error("Ad Error:", e);
                    // Agar koi error aaye to bhi verify kar do (User khush rahega)
                    window.location.href = verifyLink;
                }}
            }}
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
        
        amount = round(random.uniform(5.00, 10.00), 2)
        inc_balance(uid, amount)
        inc_ads(uid)
        
        return redirect(f"tg://resolve?domain={BOT_USERNAME}&start=verified_{amount}")
    except:
        return "Error"

# --- BOT COMMANDS (Old Standard) ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if len(message.text.split()) > 1 and message.text.split()[1].startswith("verified_"):
        amt = message.text.split("_")[1]
        bot.reply_to(message, f"✅ **Shabash!**\n\n💰 **+₹{amt}** wallet me add ho gaye.", reply_markup=main_menu())
        return

    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ **Channel Join Karo!**", reply_markup=force_sub_markup())
        return
    
    get_user(user_id, message.from_user.username)
    bot.reply_to(message, f"👋 **Namaste {message.from_user.first_name}!**\nMoneyTube me swagat hai. 💸", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🎬 Watch & Earn 🤑")
def watch_ad(message):
    if not SITE_URL: 
        bot.reply_to(message, "❌ Error: SITE_URL missing")
        return
    
    user_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    # WebApp Use karna taaki Telegram ke andar hi khule
    web_app = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Watch Video (Click)", web_app=web_app))
    
    bot.reply_to(message, "👇 **Niche button dabao aur Ad Dekho:**", reply_markup=markup)

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
    return "✅ MoneyTube v9.1 (Final SDK Integrated) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
