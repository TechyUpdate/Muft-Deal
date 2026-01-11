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

# --- CONFIGURATION (Baki sab same hai) ---
TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MoneyTubeBot").replace("@", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "") 
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "") 
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
MONGO_URI = os.environ.get("MONGO_URI", "")
AD_LINK = os.environ.get("AD_LINK", "https://google.com") 
SITE_URL = os.environ.get("SITE_URL", "") 
SUPPORT_USER = os.environ.get("SUPPORT_USER", "Admin") # Ye Render se aayega

# --- DATABASE (NO CHANGES) ---
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

# --- HELPERS (NO CHANGES) ---
def send_log(text):
    if LOG_CHANNEL:
        try: bot.send_message(LOG_CHANNEL, text, parse_mode="Markdown")
        except: pass

def get_user(user_id, username=None):
    if db is None: return {} 
    user = users_col.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id, "balance": 0.0, "invites": 0, "ads_watched": 0, "withdraw_count": 0,
            "last_bonus": None, "joined_via": None, "status": "Bronze Member 🥉",
            "username": username, "joined_date": str(date.today())
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

def get_time_remaining():
    now = datetime.now()
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining = midnight - now
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

# --- WEB APP ROUTE (UI UPDATED: JANDAR LOOK & BUTTON FIX) ---
@server.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    if not user_id: return "Error: User ID Missing"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Watch & Earn</title>
        <style>
            body {{ background-color: #050505; color: white; font-family: 'Arial', sans-serif; text-align: center; margin: 0; padding: 15px; }}
            .container {{ margin-top: 10px; }}
            
            /* JANDAR HEADER */
            h3 {{ 
                color: #00ff88; 
                text-transform: uppercase; 
                letter-spacing: 1px; 
                text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
                margin-bottom: 5px;
            }}
            
            /* VIDEO BOX STYLING */
            .video-box {{ 
                width: 100%; height: 260px; 
                background: #000; 
                display: flex; align-items: center; justify-content: center;
                border-radius: 15px; margin-bottom: 20px; cursor: pointer;
                background-image: url('https://img.freepik.com/free-vector/video-player-template_23-2148524458.jpg');
                background-size: cover; 
                border: 3px solid #333; 
                position: relative;
                box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
                transition: transform 0.1s;
            }}
            .video-box:active {{ transform: scale(0.98); }}
            
            .play-btn {{ 
                font-size: 70px; color: #fff; 
                background: rgba(0,0,0,0.6); 
                padding: 10px 30px; border-radius: 50%; 
                border: 2px solid #00ff88;
                box-shadow: 0 0 15px #00ff88;
            }}
            
            /* PROGRESS BAR - CHAMAKDAR */
            .progress-container {{ 
                width: 100%; background-color: #222; 
                height: 15px; border-radius: 10px; 
                overflow: hidden; margin-top: 15px; 
                border: 1px solid #444;
            }}
            .progress-bar {{ 
                width: 0%; height: 100%; 
                background: linear-gradient(90deg, #00C853, #64DD17); 
                transition: width 0.15s linear; 
                box-shadow: 0 0 10px #64DD17;
            }}
            
            .timer-text {{ margin-top: 12px; font-size: 18px; font-weight: bold; color: #FFD700; }}
            
            /* REDIRECT BUTTON (THE FIX) */
            #claimBtn {{
                display: none; /* Pehle chhupa rahega */
                background: linear-gradient(45deg, #FFD700, #FF8C00);
                color: black; font-weight: bold; font-size: 20px;
                padding: 15px 30px; border: none; border-radius: 50px;
                margin-top: 20px; width: 80%; cursor: pointer;
                box-shadow: 0 0 20px rgba(255, 215, 0, 0.6);
                animation: pulse 1.5s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
                100% {{ transform: scale(1); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h3>💰 Watch 15 Seconds</h3>
            <p style="font-size: 13px; color: #aaa;">Pura dekhne par hi paisa milega</p>
            
            <div class="video-box" onclick="startAd()">
                <div class="play-btn" id="playIcon">▶</div>
            </div>

            <div class="progress-container">
                <div id="bar" class="progress-bar"></div>
            </div>
            
            <div class="timer-text" id="status">Tap ▶ to Start</div>
            
            <button id="claimBtn" onclick="claimReward()">💰 CLAIM ₹10 NOW</button>
        </div>

        <script>
            let clicked = false;
            let userId = "{user_id}";
            let siteUrl = "{SITE_URL}";
            
            function startAd() {{
                if (clicked) return;
                clicked = true;
                
                // 1. OPEN AD
                window.open("{AD_LINK}", "_blank");
                
                document.getElementById('playIcon').style.display = 'none';
                document.getElementById('status').innerText = "⏳ Watching Ad... 15s";
                
                // 2. START TIMER
                let bar = document.getElementById('bar');
                let width = 0;
                let interval = setInterval(function() {{
                    width += 1;
                    bar.style.width = width + '%';
                    
                    let secLeft = 15 - Math.floor((width/100)*15);
                    if(secLeft < 0) secLeft = 0;
                    document.getElementById('status').innerText = "⏳ Time Remaining: " + secLeft + "s";
                    
                    if (width >= 100) {{
                        clearInterval(interval);
                        document.getElementById('status').innerText = "✅ Task Completed!";
                        document.getElementById('status').style.color = "#00ff88";
                        
                        // 3. SHOW BUTTON instead of weak Auto Redirect
                        document.getElementById('claimBtn').style.display = "inline-block";
                        
                        // Koshish karo auto redirect ki, agar fail hua to button hai hi
                        setTimeout(function() {{
                            window.location.href = siteUrl + "/verify?user_id=" + userId;
                        }}, 1000);
                    }}
                }}, 150);
            }}

            function claimReward() {{
                window.location.href = siteUrl + "/verify?user_id=" + userId;
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
        # Database check (Crash fix included)
        user = get_user(uid)
        
        amount = round(random.uniform(5.00, 10.00), 2)
        inc_balance(uid, amount)
        inc_ads(uid)
        
        send_log(f"🎬 **Ad Watched**\nUser: `{uid}`\nEarned: ₹{amount}")
        
        # Server-Side Redirect back to Telegram
        return redirect(f"https://t.me/{BOT_USERNAME}?start=verified_{amount}")
    except Exception as e:
        return f"❌ Error: {e}"

# --- BOT COMMANDS (Logic same as v2.2) ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    
    # Auto-Return Handling
    if len(message.text.split()) > 1 and message.text.split()[1].startswith("verified_"):
        amount = message.text.split("_")[1]
        bot.reply_to(message, f"✅ **Paisa Mil Gaya!**\n\n💰 **+₹{amount}** added to wallet.", reply_markup=main_menu())
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
        bot.reply_to(message, "❌ **Error:** Render me SITE_URL set nahi hai.")
        return

    markup = types.InlineKeyboardMarkup()
    web_app_info = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Video Dekho (Click)", web_app=web_app_info))
    
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
        bal = user.get('balance', 0.0)
        ads = user.get('ads_watched', 0)
        inv = user.get('invites', 0)
        bot.reply_to(message, f"💳 **Aapka Account**\n\n💰 Balance: ₹{round(bal, 2)}\n📺 Ads Watched: {ads}\n👥 Total Referrals: {inv}")
        
    elif text == "🎁 Daily Bonus":
        today = str(date.today())
        if user.get('last_bonus') == today:
            time_left = get_time_remaining()
            bot.reply_to(message, f"❌ **Bonus le liya!**\n\n⏳ Agla bonus: {time_left} baad aana.")
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
         share_url = f"https://t.me/share/url?url={ref_link}&text=Join this bot and earn money!"
         markup.add(types.InlineKeyboardButton("🚀 Share Link", url=share_url))
         bot.reply_to(message, f"📣 **Refer & Earn**\n\nHar dost par ₹40 kamao! Niche button se share karo.", reply_markup=markup)

    elif text == "⚙️ Settings":
        bot.reply_to(message, "👇 **Options:**", reply_markup=extra_menu())

    elif text == "🆘 Support":
        # FIX: Variable sahi kar diya
        support = SUPPORT_USER.replace("@", "")
        bot.reply_to(message, f"📞 **Support:** @{support}")
        
    elif text == "📢 Updates":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.reply_to(message, "Niche click karke updates dekhein:", reply_markup=markup)

    elif text == "❓ FAQ":
        msg = ("❓ **FAQ (Sawal-Jawab)**\n\n"
               "Q: **Paise kaise kamayein?**\nA: 'Watch Ad' par click karein aur 15 sec wait karein.\n\n"
               "Q: **Withdraw kab hoga?**\nA: Min ₹300 aur 5 Refers hone par.\n\n"
               "Q: **Payment Method?**\nA: Paytm, UPI aur Bank.")
        bot.reply_to(message, msg)

    elif text == "💸 Paisa Nikalo":
        bot.reply_to(message, "🏧 **Kahan paise lene hain?**", reply_markup=withdraw_menu())
        
    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 **Home**", reply_markup=main_menu())

    elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
         w_count = user.get('withdraw_count', 0)
         bal = user.get('balance', 0.0)
         
         # FIX: Support user variable here too
         support = SUPPORT_USER.replace("@", "")

         if w_count == 0: 
             if bal < 10:
                 bot.reply_to(message, f"❌ **Balance Kam Hai!**\nPehli baar ke liye ₹10 chahiye.")
             else:
                 inc_withdraw_count(user_id)
                 bot.reply_to(message, f"✅ **Request Leli Gayi Hai!**\n\nApna Number/UPI mujhe DM karein @{support}.")
                 send_log(f"💸 **FIRST WITHDRAWAL**\nUser: `{user_id}`\nAmt: ₹{bal}\nMethod: {text}")

         else: 
             if bal < 300:
                  bot.reply_to(message, f"❌ **Min Withdraw: ₹300**\nAbhi Balance: ₹{round(bal, 2)}")
             elif user.get('invites', 0) < 5:
                  bot.reply_to(message, f"❌ **Task Baki Hai!**\n5 Doston ko invite karein.")
             else:
                  inc_withdraw_count(user_id)
                  bot.reply_to(message, "✅ **Request Submitted!**\nAdmin jald hi bhejenve.")
                  send_log(f"💸 **WITHDRAWAL**\nUser: `{user_id}`\nAmt: ₹{bal}\nMethod: {text}")

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🎬 Watch & Earn 🤑")
    markup.row("💼 My Account", "💸 Paisa Nikalo")
    markup.row("🎁 Daily Bonus", "🚀 Share & Loot")
    markup.row("👤 VIP Profile", "⚙️ Settings")
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
    return "✅ MoneyTube v2.3 (Jandar UI + Redirect Button Fix) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
