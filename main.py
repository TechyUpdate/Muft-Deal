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
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "") 
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "") 
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
MONGO_URI = os.environ.get("MONGO_URI", "")
AD_LINK = os.environ.get("AD_LINK", "https://google.com") # Adsterra Link

# ⚠️ Render App URL (Zaroori hai) - Ex: https://moneytube.onrender.com
SITE_URL = os.environ.get("SITE_URL", "") 

# --- DATABASE ---
if not MONGO_URI:
    print("❌ Error: MONGO_URI missing!")
    db = None
else:
    try:
        client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client['moneytube_db']
        users_col = db['users']
        print("✅ MongoDB Connected!")
    except:
        db = None

bot = telebot.TeleBot(TOKEN) if TOKEN else None
server = Flask(__name__)

# --- HELPERS ---
def send_log(text):
    if LOG_CHANNEL:
        try: bot.send_message(LOG_CHANNEL, text, parse_mode="Markdown")
        except: pass

def get_user(user_id, username=None):
    if db is None: return {} 
    user = users_col.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id, "balance": 0.0, "invites": 0, "ads_watched": 0,
            "last_bonus": None, "joined_via": None, "status": "Bronze Member 🥉",
            "username": username, "joined_date": str(date.today())
        }
        users_col.insert_one(user)
    return user

def update_user(user_id, data):
    if db: users_col.update_one({"_id": user_id}, {"$set": data})

def inc_balance(user_id, amount):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})

def inc_ads(user_id):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"ads_watched": 1}})

def inc_invites(user_id):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"invites": 1}})

def is_user_member(user_id):
    if not CHANNEL_USERNAME: return True 
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['creator', 'administrator', 'member']
    except: return True 

def get_time_remaining():
    now = datetime.now()
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining = midnight - now
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

# --- WEB APP ROUTE (Auto Redirect) ---
@server.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    if not user_id: return "Error: User ID Missing"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Watching Ad...</title>
        <style>
            body {{ background-color: #000; color: white; font-family: sans-serif; text-align: center; margin: 0; padding: 20px; }}
            .container {{ margin-top: 60px; }}
            .video-box {{ 
                width: 100%; height: 220px; background: #222; 
                display: flex; align-items: center; justify-content: center;
                border-radius: 12px; margin-bottom: 25px; cursor: pointer;
                background-image: url('https://img.freepik.com/free-vector/video-player-template_23-2148524458.jpg');
                background-size: cover; border: 2px solid #333;
            }}
            .play-icon {{ font-size: 60px; color: white; background: rgba(0,0,0,0.6); padding: 15px 25px; border-radius: 50%; }}
            
            /* Progress Bar */
            .progress-bg {{ width: 100%; background-color: #333; height: 8px; border-radius: 4px; overflow: hidden; }}
            .progress-fill {{ width: 0%; height: 100%; background-color: #00E676; transition: width 0.2s linear; }}
            
            .status {{ margin-top: 15px; font-size: 16px; color: #aaa; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h3>💰 Watch to Earn ₹5 - ₹10</h3>
            
            <div class="video-box" onclick="startAdFlow()">
                <div class="play-icon">▶</div>
            </div>

            <div class="progress-bg">
                <div id="fill" class="progress-fill"></div>
            </div>
            <p class="status" id="statusMsg">Click Play to Start</p>
        </div>

        <script>
            let started = false;
            
            function startAdFlow() {{
                if (started) return;
                started = true;
                
                // 1. Open Adsterra Ad
                window.open("{AD_LINK}", "_blank");
                
                document.getElementById('statusMsg').innerText = "Ad Playing... Wait 15 Seconds";
                
                // 2. Start Timer & Progress Bar
                let fill = document.getElementById('fill');
                let width = 0;
                let interval = setInterval(function() {{
                    width += 1;
                    fill.style.width = width + '%';
                    
                    if (width >= 100) {{
                        clearInterval(interval);
                        document.getElementById('statusMsg').innerText = "✅ Done! Redirecting...";
                        document.getElementById('statusMsg').style.color = "#00E676";
                        
                        // 3. AUTO REDIRECT (No Click Needed)
                        setTimeout(function() {{
                            window.location.href = "{SITE_URL}/verify?user_id={user_id}";
                        }}, 1000);
                    }}
                }}, 150); // 150ms * 100 = 15 Seconds Total
            }}
        </script>
    </body>
    </html>
    """
    return html

@server.route('/verify')
def verify_task():
    user_id = request.args.get('user_id')
    if not user_id: return "Error"
    
    uid = int(user_id)
    # INCREASED REWARD: ₹5 to ₹10
    amount = round(random.uniform(5.00, 10.00), 2)
    
    inc_balance(uid, amount)
    inc_ads(uid)
    send_log(f"🎬 **Ad Watched**\nUser: `{uid}`\nEarned: ₹{amount}")
    
    # Auto Close Window & Back to Bot
    return redirect(f"https://t.me/{BOT_USERNAME}?start=verified_{amount}")

# --- BOT HANDLERS ---
@bot.message_handler(func=lambda m: m.text == "▶️ Ad Dekho")
def watch_video_ad(message):
    user_id = message.chat.id
    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ Join Channel First!", reply_markup=force_sub_markup())
        return
        
    if not SITE_URL:
        bot.reply_to(message, "❌ **Error:** Admin ne `SITE_URL` set nahi kiya.")
        return

    markup = types.InlineKeyboardMarkup()
    web_app_info = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Watch Video Ad", web_app=web_app_info))
    
    bot.reply_to(message, "👇 **Click below to Watch:**", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    
    # Handle Auto-Return from Ad
    if len(message.text.split()) > 1 and message.text.split()[1].startswith("verified_"):
        amount = message.text.split("_")[1]
        bot.reply_to(message, f"✅ **Task Completed!**\n\n💰 **+₹{amount}** Added to Wallet.", reply_markup=main_menu())
        return

    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ Join Channel First!", reply_markup=force_sub_markup())
        return
    
    get_user(user_id, message.from_user.username)
    
    # Check for referral
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id:
        referrer_id = int(args[1])
        user = get_user(user_id)
        if user['joined_via'] is None:
            update_user(user_id, {"joined_via": referrer_id})
            inc_balance(referrer_id, 40.0)
            inc_invites(referrer_id)
            try: bot.send_message(referrer_id, "🌟 **Referral Bonus: +₹40**")
            except: pass

    bot.reply_to(message, "👋 Welcome to MoneyTube!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.chat.id
    if not is_user_member(user_id):
         bot.reply_to(message, "⚠️ Join Channel First!", reply_markup=force_sub_markup())
         return

    user = get_user(user_id)
    text = message.text
    
    if text == "💰 My Wallet":
        bot.reply_to(message, f"💳 **Wallet**\n💰 Balance: ₹{round(user['balance'], 2)}\n📺 Ads: {user['ads_watched']}\n👥 Refers: {user['invites']}")
        
    elif text == "🎁 Daily Bonus":
        today = str(date.today())
        if user.get('last_bonus') == today:
            time_left = get_time_remaining()
            bot.reply_to(message, f"❌ **Claimed!**\n⏳ Next: {time_left}")
        else:
            # INCREASED BONUS: ₹10 to ₹20
            bonus = round(random.uniform(10.00, 20.00), 2)
            inc_balance(user_id, bonus)
            update_user(user_id, {"last_bonus": today})
            bot.reply_to(message, f"🎁 **Daily Bonus!**\n+₹{bonus} added.")

    elif text == "⚙️ Extra":
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("Withdrawal History", "Updates", "FAQ", "Support", "🔙 Main Menu")
        bot.reply_to(message, "Select Option:", reply_markup=markup)

    elif text == "🏦 Withdraw Money":
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer", "🔙 Main Menu")
        bot.reply_to(message, "Select Method:", reply_markup=markup)

    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 Home", reply_markup=main_menu())
        
    elif text == "👥 Refer & Earn":
         ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
         bot.reply_to(message, f"📣 **Refer & Earn**\n\n₹40 per invite!\nLink: `{ref_link}`")

    # Payment Methods
    elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
         if user['balance'] < 300:
             bot.reply_to(message, f"❌ **Low Balance!**\nMin Withdraw: ₹300\nYour Balance: ₹{round(user['balance'], 2)}")
         else:
             bot.reply_to(message, "✅ **Request Submitted!**")
             send_log(f"💸 **WITHDRAWAL**\nUser: `{user_id}`\nAmount: ₹{round(user['balance'], 2)}")

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("▶️ Ad Dekho", "💰 My Wallet", "🎁 Daily Bonus", "🏦 Withdraw Money", "👥 Refer & Earn", "⚙️ Extra")
    return markup

def force_sub_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Check", callback_data="check_join"))
    return markup

# --- SERVER RUNNER ---
@server.route('/')
def home():
    return "✅ MoneyTube v1.8 (Auto Redirect) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
