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
# Fix: Username without @
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MoneyTubeBot").replace("@", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "") 
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "") 
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
MONGO_URI = os.environ.get("MONGO_URI", "")
AD_LINK = os.environ.get("AD_LINK", "https://google.com") 
SITE_URL = os.environ.get("SITE_URL", "") 
SUPPORT_USER = os.environ.get("SUPPORT_USER", "Admin")

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
            "_id": user_id, 
            "balance": 0.0, 
            "invites": 0, 
            "ads_watched": 0,
            "withdraw_count": 0,
            "last_bonus": None, 
            "joined_via": None, 
            "status": "Bronze Member 🥉",
            "username": username, 
            "joined_date": str(date.today())
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

def inc_withdraw_count(user_id):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"withdraw_count": 1}})

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

# --- WEB APP ROUTE (FIXED UI & REDIRECT) ---
@server.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    if not user_id: return "Error: User ID Missing"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Watch Ad</title>
        <style>
            body {{ background-color: #000; color: white; font-family: sans-serif; text-align: center; margin: 0; padding: 10px; }}
            .container {{ margin-top: 30px; }}
            h3 {{ color: #4CAF50; margin-bottom: 10px; }}
            
            /* CLICKABLE VIDEO CONTAINER */
            .video-box {{ 
                width: 100%; height: 250px; background: #222; 
                display: flex; align-items: center; justify-content: center;
                border-radius: 10px; margin-bottom: 20px; cursor: pointer;
                background-image: url('https://img.freepik.com/free-vector/video-player-template_23-2148524458.jpg');
                background-size: cover; border: 2px solid #555; position: relative;
            }}
            .play-btn {{ font-size: 60px; color: white; background: rgba(0,0,0,0.7); padding: 10px 25px; border-radius: 50%; }}
            
            /* PROGRESS BAR (LINING) */
            .progress-container {{ width: 100%; background-color: #333; height: 12px; border-radius: 6px; overflow: hidden; margin-top: 10px; }}
            .progress-bar {{ width: 0%; height: 100%; background-color: #2196F3; transition: width 0.15s linear; }}
            
            .timer-text {{ margin-top: 10px; font-size: 18px; font-weight: bold; color: #FFD700; }}
            .hint {{ font-size: 12px; color: #888; margin-top: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h3>💰 Watch 15 Seconds</h3>
            
            <div class="video-box" onclick="startAd()">
                <div class="play-btn" id="playIcon">▶</div>
            </div>

            <div class="progress-container">
                <div id="bar" class="progress-bar"></div>
            </div>
            
            <div class="timer-text" id="status">Click ▶ to Start</div>
            <div class="hint">Do not close window</div>
        </div>

        <script>
            let clicked = false;
            
            function startAd() {{
                if (clicked) return;
                clicked = true;
                
                // 1. Direct Ad Open
                window.open("{AD_LINK}", "_blank");
                
                document.getElementById('playIcon').style.display = 'none';
                document.getElementById('status').innerText = "⏳ Watching... 15s";
                
                // 2. Lining Animation
                let bar = document.getElementById('bar');
                let width = 0;
                let interval = setInterval(function() {{
                    width += 1;
                    bar.style.width = width + '%';
                    
                    // Show Seconds logic (approx)
                    let secLeft = 15 - Math.floor((width/100)*15);
                    document.getElementById('status').innerText = "⏳ Watching... " + secLeft + "s";
                    
                    if (width >= 100) {{
                        clearInterval(interval);
                        document.getElementById('status').innerText = "✅ Done! Redirecting...";
                        document.getElementById('status').style.color = "#4CAF50";
                        
                        // 3. Auto Redirect
                        setTimeout(function() {{
                            window.location.href = "{SITE_URL}/verify?user_id={user_id}";
                        }}, 1000);
                    }}
                }}, 150);
            }}
        </script>
    </body>
    </html>
    """
    return html

@server.route('/verify')
def verify_task():
    try:
        user_id = request.args.get('user_id')
        if not user_id: return "Error"
        
        uid = int(user_id)
        # Database Error Fix: Use 'is not None'
        user = get_user(uid)
        
        amount = round(random.uniform(5.00, 10.00), 2)
        inc_balance(uid, amount)
        inc_ads(uid)
        
        send_log(f"🎬 **Ad Watched**\nUser: `{uid}`\nEarned: ₹{amount}")
        
        return redirect(f"https://t.me/{BOT_USERNAME}?start=verified_{amount}")
    except Exception as e:
        return f"Error: {e}"

# --- BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    
    # Auto-Return Handling
    if len(message.text.split()) > 1 and message.text.split()[1].startswith("verified_"):
        amount = message.text.split("_")[1]
        bot.reply_to(message, f"✅ **Shabash!**\n\n💰 **+₹{amount}** added to wallet.", reply_markup=main_menu())
        return

    if not is_user_member(user_id):
        bot.reply_to(message, f"👋 **Namaste {message.from_user.first_name}!**\n\nPehle Channel Join karein.", reply_markup=force_sub_markup())
        return
    
    get_user(user_id, message.from_user.username)
    
    # Referral Logic
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id:
        referrer_id = int(args[1])
        user = get_user(user_id)
        if user['joined_via'] is None:
            update_user(user_id, {"joined_via": referrer_id})
            inc_balance(referrer_id, 40.0)
            inc_invites(referrer_id)
            try: bot.send_message(referrer_id, "🌟 **Naya Dost Aaya!**\nReferral Bonus: +₹40")
            except: pass

    bot.reply_to(message, f"👋 **Namaste {message.from_user.first_name}!**\nMoneyTube me swagat hai. 💸", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🎬 Watch & Earn 🤑")
def watch_video_ad(message):
    user_id = message.chat.id
    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ **Channel Join Karo!**", reply_markup=force_sub_markup())
        return

    if not SITE_URL:
        bot.reply_to(message, "❌ **Error:** Admin Render URL check karein.")
        return

    markup = types.InlineKeyboardMarkup()
    web_app_info = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Watch Video (Click)", web_app=web_app_info))
    
    bot.reply_to(message, "👇 **Niche button dabao aur Video Dekho:**", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.chat.id
    if not is_user_member(user_id):
         bot.reply_to(message, "⚠️ **Channel Join Karo!**", reply_markup=force_sub_markup())
         return

    user = get_user(user_id)
    text = message.text
    
    if text == "💼 My Account":
        # Database Crash Fix
        bal = user.get('balance', 0.0)
        ads = user.get('ads_watched', 0)
        inv = user.get('invites', 0)
        bot.reply_to(message, f"💳 **Aapka Account**\n\n💰 Balance: ₹{round(bal, 2)}\n📺 Ads Watched: {ads}\n👥 Total Referrals: {inv}")
        
    elif text == "🎁 Free Bonus":
        today = str(date.today())
        if user.get('last_bonus') == today:
            bot.reply_to(message, f"❌ **Bonus le liya!**\n\n⏳ Agla bonus kal milega.")
        else:
            bonus = round(random.uniform(10.00, 20.00), 2)
            inc_balance(user_id, bonus)
            update_user(user_id, {"last_bonus": today})
            bot.reply_to(message, f"🎁 **Bonus Mil Gaya!**\n+₹{bonus} added.")

    elif text == "👤 VIP Profile":
         # NEW PROFILE SECTION
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
         # Fix: Button Logic instead of plain text
         ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
         markup = types.InlineKeyboardMarkup()
         share_url = f"https://t.me/share/url?url={ref_link}&text=Join this bot and earn money!"
         markup.add(types.InlineKeyboardButton("🚀 Share with Friends", url=share_url))
         
         bot.reply_to(message, f"📣 **Refer & Earn**\n\nHar dost par ₹40 kamao!\n\nLink:\n`{ref_link}`", reply_markup=markup)

    elif text == "⚙️ Settings":
        bot.reply_to(message, "👇 **Options:**", reply_markup=extra_menu())

    elif text == "🆘 Support":
        # Fix: Show Admin Username
        bot.reply_to(message, f"📞 **Support:** @{SUPPORT_USER}")
        
    elif text == "📢 Updates":
        # Fix: Button for Channel
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.reply_to(message, "Niche click karke updates dekhein:", reply_markup=markup)

    elif text == "❓ FAQ":
        # Fix: Better Language
        msg = ("❓ **FAQ (Sawal-Jawab)**\n\n"
               "Q: **Paise kaise kamayein?**\nA: 'Watch Ad' par click karein aur 15 sec wait karein.\n\n"
               "Q: **Withdraw kab hoga?**\nA: Min ₹300 aur 5 Refers hone par.\n\n"
               "Q: **Payment Method?**\nA: Paytm, UPI aur Bank.")
        bot.reply_to(message, msg)

    elif text == "💸 Paisa Nikalo":
        bot.reply_to(message, "🏧 **Kahan paise lene hain?**", reply_markup=withdraw_menu())
        
    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 **Home**", reply_markup=main_menu())

    # WITHDRAWAL LOGIC (Silent Fix)
    elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
         w_count = user.get('withdraw_count', 0)
         bal = user.get('balance', 0.0)
         
         if w_count == 0: # First Time
             if bal < 10:
                 bot.reply_to(message, f"❌ **Balance Kam Hai!**\nPehli baar ke liye ₹10 chahiye.")
             else:
                 inc_withdraw_count(user_id)
                 bot.reply_to(message, "✅ **Request Leli Gayi Hai!**\n\nApna Number/UPI mujhe DM karein @{SUPPORT_USER}.")
                 send_log(f"💸 **FIRST WITHDRAWAL**\nUser: `{user_id}`\nAmt: ₹{bal}\nMethod: {text}")

         else: # Next Times
             if bal < 300:
                  bot.reply_to(message, f"❌ **Min Withdraw: ₹300**\nAbhi Balance: ₹{round(bal, 2)}")
             elif user.get('invites', 0) < 5:
                  bot.reply_to(message, f"❌ **Task Baki Hai!**\n5 Doston ko invite karein.")
             else:
                  inc_withdraw_count(user_id)
                  bot.reply_to(message, "✅ **Request Submitted!**\nAdmin jald hi bhejenve.")
                  send_log(f"💸 **WITHDRAWAL**\nUser: `{user_id}`\nAmt: ₹{bal}\nMethod: {text}")

# --- MENUS (New Stylish Names) ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    # Buttons renamed to be Unique
    markup.add("🎬 Watch & Earn 🤑", "💼 My Account")
    markup.add("🎁 Free Bonus", "💸 Paisa Nikalo")
    markup.add("👤 VIP Profile", "🚀 Share & Loot")
    markup.add("⚙️ Settings")
    return markup

def extra_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🆘 Support", "📢 Updates", "❓ FAQ", "🔙 Main Menu")
    return markup

def withdraw_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer", "🔙 Main Menu")
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
        bot.answer_callback_query(call.id, "✅ Verified!")
        bot.send_message(call.message.chat.id, "🏠 **Main Menu**", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ Not Joined Yet!", show_alert=True)

# --- SERVER ---
@server.route('/')
def home():
    return "✅ MoneyTube v2.1 (Unique Style + Profile) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
