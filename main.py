import telebot
from telebot import types
from flask import Flask, request, redirect
from threading import Thread
import os
import random
from datetime import date, datetime, timedelta
import pymongo
import certifi

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MoneyTubeBot").replace("@", "")

# TERA ADSTERRA LINK
AD_LINK = os.environ.get("AD_LINK", "https://google.com") 

# TERA RENDER URL (No Slash at end)
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

# --- 1. THE DHANTUBE CLONE PAGE (Exact Interface) ---
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
        <title>Watch Video</title>
        <style>
            /* DHANTUBE DARK THEME */
            body {{
                background-color: #000000;
                color: white;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
            }}
            
            /* HEADER TEXT */
            .header-text {{
                color: #4CAF50; /* Green Text */
                font-weight: bold;
                font-size: 18px;
                margin-bottom: 5px;
                display: flex; align-items: center; gap: 5px;
            }}

            .sub-text {{
                color: #888;
                font-size: 12px;
                margin-bottom: 20px;
            }}

            /* VIDEO PLAYER BOX */
            .video-wrapper {{
                position: relative;
                width: 90%;
                max-width: 400px;
                aspect-ratio: 16/9;
                background-color: #111;
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid #333;
                background-image: url('https://img.freepik.com/free-vector/video-player-template_23-2148524458.jpg'); /* Fake Thumbnail */
                background-size: cover;
                background-position: center;
                box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
            }}

            /* PLAY BUTTON OVERLAY */
            .play-overlay {{
                position: absolute;
                top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.4);
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                z-index: 5;
            }}

            .play-btn-circle {{
                width: 60px; height: 60px;
                background: rgba(255,255,255,0.2);
                border-radius: 50%;
                display: flex; align-items: center; justify-content: center;
                backdrop-filter: blur(5px);
            }}
            
            .play-triangle {{
                width: 0; 
                height: 0; 
                border-top: 10px solid transparent;
                border-bottom: 10px solid transparent;
                border-left: 18px solid white;
                margin-left: 4px;
            }}

            /* PROGRESS BAR CONTAINER */
            .progress-area {{
                width: 90%;
                max-width: 400px;
                height: 4px;
                background-color: #333;
                border-radius: 2px;
                margin-top: 15px;
                overflow: hidden;
                display: none; /* Hidden initially */
            }}

            /* BLUE LINE (DhanTube Style) */
            .progress-fill {{
                width: 0%;
                height: 100%;
                background-color: #2196F3; /* Bright Blue */
                transition: width 0.1s linear;
            }}

            /* STATUS TEXT */
            .status-msg {{
                margin-top: 15px;
                color: #aaa;
                font-size: 14px;
                font-weight: 500;
            }}
            
            /* INVISIBLE CLICK TRAP */
            .click-trap {{
                position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10;
            }}

        </style>
    </head>
    <body>

        <div class="header-text">
            💰 Watch 15 Seconds
        </div>
        <div class="sub-text">Click Play to Start Earning</div>

        <div class="video-wrapper" id="videoBox">
            <div class="play-overlay" id="playBtn">
                <div class="play-btn-circle">
                    <div class="play-triangle"></div>
                </div>
            </div>
            <div class="click-trap" onclick="startFlow()"></div>
        </div>

        <div class="progress-area" id="progressBox">
            <div class="progress-fill" id="progressBar"></div>
        </div>

        <div class="status-msg" id="statusText">Wait...</div>

        <script>
            let adLink = "{AD_LINK}";
            let verifyLink = "{SITE_URL}/verify?user_id={user_id}";
            let clicked = false;

            function startFlow() {{
                if(clicked) return;
                clicked = true;

                // 1. OPEN ADSTERRA (New Tab)
                window.open(adLink, "_blank");

                // 2. UI TRANSFORMATION
                document.getElementById('playBtn').style.display = 'none'; // Hide Play Button
                document.getElementById('progressBox').style.display = 'block'; // Show Line
                document.getElementById('statusText').innerText = "Watching Ad...";
                document.getElementById('statusText').style.color = "#2196F3"; // Blue Text

                // 3. START TIMER (15 Seconds)
                let bar = document.getElementById('progressBar');
                let width = 0;
                
                // 100 steps * 150ms = 15 Seconds
                let interval = setInterval(() => {{
                    width += 1;
                    bar.style.width = width + '%';
                    
                    if(width >= 100) {{
                        clearInterval(interval);
                        document.getElementById('statusText').innerText = "Redirecting...";
                        document.getElementById('statusText').style.color = "#4CAF50"; // Green
                        
                        // 4. AUTO REDIRECT TO TELEGRAM
                        window.location.href = verifyLink;
                    }}
                }}, 150);
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
        
        # Add Money
        amount = round(random.uniform(5.00, 10.00), 2)
        inc_balance(uid, amount)
        inc_ads(uid)
        
        # Open Telegram App Directly
        return redirect(f"tg://resolve?domain={BOT_USERNAME}&start=verified_{amount}")
    except:
        return "Error"

# --- BOT COMMANDS (Old Config Restored) ---

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
    
    # Referral
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id:
        ref_id = int(args[1])
        user = get_user(user_id)
        if user['joined_via'] is None:
            update_user(user_id, {"joined_via": ref_id})
            inc_balance(ref_id, 40.0)
            inc_invites(ref_id)
            try: bot.send_message(ref_id, "🌟 **Referral Bonus:** +₹40")
            except: pass

    bot.reply_to(message, f"👋 **Namaste {message.from_user.first_name}!**\nMoneyTube me swagat hai. 💸", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🎬 Watch & Earn 🤑")
def watch_ad(message):
    if not SITE_URL: 
        bot.reply_to(message, "❌ Error: SITE_URL missing")
        return
    
    user_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Watch Video (Click)", web_app=web_app))
    
    bot.reply_to(message, "👇 **Niche button dabao aur Ad Dekho:**", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.chat.id
    if not is_user_member(user_id):
         bot.reply_to(message, "⚠️ **Channel Join Karo!**", reply_markup=force_sub_markup())
         return

    user = get_user(user_id)
    text = message.text
    
    if text == "💼 My Account":
        bal = user.get('balance', 0.0)
        ads = user.get('ads_watched', 0)
        inv = user.get('invites', 0)
        bot.reply_to(message, f"💳 **Aapka Account**\n\n💰 Balance: ₹{round(bal, 2)}\n📺 Ads Watched: {ads}\n👥 Total Referrals: {inv}")
        
    elif text == "🎁 Daily Bonus":
        today = str(date.today())
        if user.get('last_bonus') == today:
            bot.reply_to(message, f"❌ **Bonus le liya!**\n\n⏳ Agla bonus kal milega.")
        else:
            bonus = round(random.uniform(10.00, 20.00), 2)
            inc_balance(user_id, bonus)
            update_user(user_id, {"last_bonus": today})
            bot.reply_to(message, f"🎁 **Bonus Mil Gaya!**\n+₹{bonus} added.")

    elif text == "👤 VIP Profile":
         bal = user.get('balance', 0.0)
         status = user.get('status', 'Bronze Member 🥉')
         doj = user.get('joined_date', 'Unknown')
         msg = (f"👤 **USER PROFILE**\n"
                f"━━━━━━━━━━━━━━\n"
                f"🆔 ID: `{user_id}`\n"
                f"📛 Name: {message.from_user.first_name}\n"
                f"🏆 Status: **{status}**\n"
                f"📅 Joined: {doj}\n"
                f"💰 Earnings: ₹{round(bal, 2)}\n"
                f"━━━━━━━━━━━━━━")
         bot.reply_to(message, msg)

    elif text == "🚀 Share & Loot":
         ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
         markup = types.InlineKeyboardMarkup()
         share_url = f"https://t.me/share/url?url={ref_link}&text=Earn Money Here!"
         markup.add(types.InlineKeyboardButton("🚀 Share Link", url=share_url))
         bot.reply_to(message, f"📣 **Refer & Earn**\n\nHar dost par ₹40 kamao!", reply_markup=markup)

    elif text == "⚙️ Settings":
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("🆘 Support", "📢 Updates", "❓ FAQ", "🔙 Main Menu")
        bot.reply_to(message, "👇 **Options:**", reply_markup=markup)

    elif text == "🆘 Support":
        support = SUPPORT_USER.replace("@", "")
        bot.reply_to(message, f"📞 **Support:** @{support}")
        
    elif text == "📢 Updates":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.reply_to(message, "Updates Channel:", reply_markup=markup)

    elif text == "❓ FAQ":
        msg = ("❓ **FAQ**\n\n1. Play dabao\n2. Ad dekho\n3. Paisa kamao")
        bot.reply_to(message, msg)

    elif text == "💸 Paisa Nikalo":
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer", "🔙 Main Menu")
        bot.reply_to(message, "🏧 **Method Chuno:**", reply_markup=markup)
        
    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 **Home**", reply_markup=main_menu())

    elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
         w_count = user.get('withdraw_count', 0)
         bal = user.get('balance', 0.0)
         support = SUPPORT_USER.replace("@", "")

         if w_count == 0: 
             if bal < 10:
                 bot.reply_to(message, f"❌ **Balance Kam Hai!**\nMin: ₹10")
             else:
                 inc_withdraw_count(user_id)
                 bot.reply_to(message, f"✅ **Request Leli Gayi Hai!**\n\nDM me: @{support}")

         else: 
             if bal < 300:
                  bot.reply_to(message, f"❌ **Min Withdraw: ₹300**\nAbhi: ₹{round(bal, 2)}")
             elif user.get('invites', 0) < 5:
                  bot.reply_to(message, f"❌ **5 Refers Chahiye!**")
             else:
                  inc_withdraw_count(user_id)
                  bot.reply_to(message, "✅ **Request Submitted!**")

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
    return "✅ MoneyTube v6.0 (DhanTube Interface) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
