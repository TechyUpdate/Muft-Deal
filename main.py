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

# --- CONFIGURATION (Ye sab Render me check kar lena) ---
TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "") # Bina @ ke daalna (Ex: MoneyTubeBot)
ADMIN_ID = os.environ.get("ADMIN_ID", "") 
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "") 
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
MONGO_URI = os.environ.get("MONGO_URI", "")
AD_LINK = os.environ.get("AD_LINK", "https://google.com") 

# ⚠️ SABSE ZAROORI: Apne Render App ka Link (Last me '/' mat lagana)
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
            "_id": user_id, 
            "balance": 0.0, 
            "invites": 0, 
            "ads_watched": 0,
            "withdraw_count": 0, # New Tracker
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

# --- WEB APP ROUTE ---
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
            body {{ background-color: #000; color: white; font-family: sans-serif; text-align: center; margin: 0; padding: 20px; }}
            .container {{ margin-top: 50px; }}
            h3 {{ color: #00E676; }}
            .video-box {{ 
                width: 100%; height: 220px; background: #222; 
                display: flex; align-items: center; justify-content: center;
                border-radius: 15px; margin-bottom: 25px; cursor: pointer;
                background-image: url('https://img.freepik.com/free-vector/video-player-template_23-2148524458.jpg');
                background-size: cover; border: 2px solid #444;
            }}
            .play-icon {{ font-size: 60px; color: white; background: rgba(0,0,0,0.6); padding: 15px 25px; border-radius: 50%; }}
            
            .progress-bg {{ width: 100%; background-color: #333; height: 10px; border-radius: 5px; overflow: hidden; }}
            .progress-fill {{ width: 0%; height: 100%; background-color: #00E676; transition: width 0.15s linear; }}
            
            .status {{ margin-top: 15px; font-size: 16px; color: #aaa; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h3>🤑 Watch to Earn ₹5 - ₹10</h3>
            
            <div class="video-box" onclick="startAdFlow()">
                <div class="play-icon">▶</div>
            </div>

            <div class="progress-bg">
                <div id="fill" class="progress-fill"></div>
            </div>
            <p class="status" id="statusMsg">Play Button Dabao</p>
        </div>

        <script>
            let started = false;
            
            function startAdFlow() {{
                if (started) return;
                started = true;
                
                // 1. Open Ad
                window.open("{AD_LINK}", "_blank");
                
                document.getElementById('statusMsg').innerText = "Ad Chal Raha Hai... 15 Sec Ruko";
                
                // 2. Timer
                let fill = document.getElementById('fill');
                let width = 0;
                let interval = setInterval(function() {{
                    width += 1;
                    fill.style.width = width + '%';
                    
                    if (width >= 100) {{
                        clearInterval(interval);
                        document.getElementById('statusMsg').innerText = "✅ Done! Redirecting...";
                        document.getElementById('statusMsg').style.color = "#00E676";
                        
                        // 3. AUTO REDIRECT (Correct Logic)
                        setTimeout(function() {{
                            // Yahan error na aaye isliye SITE_URL check karna
                            window.location.href = "{SITE_URL}/verify?user_id={user_id}";
                        }}, 1500);
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
        if not user_id: return "Error: No User ID"
        
        uid = int(user_id)
        amount = round(random.uniform(5.00, 10.00), 2)
        
        inc_balance(uid, amount)
        inc_ads(uid)
        
        send_log(f"🎬 **WebApp Ad Success**\nUser: `{uid}`\nEarned: ₹{amount}")
        
        # FIX: Agar BOT_USERNAME set nahi hai to error aayega
        if not BOT_USERNAME:
            return "✅ Task Done! (Go back to Bot manually because BOT_USERNAME missing in Render)"
            
        return redirect(f"https://t.me/{BOT_USERNAME}?start=verified_{amount}")
        
    except Exception as e:
        return f"❌ Server Error: {str(e)} (Admin ko Screenshot bhejo)"

# --- BOT HANDLERS ---
@bot.message_handler(func=lambda m: m.text == "▶️ Ad Dekho")
def watch_video_ad(message):
    user_id = message.chat.id
    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ **Pehle Channel Join Karo!**", reply_markup=force_sub_markup())
        return
        
    if not SITE_URL:
        bot.reply_to(message, "❌ **Admin Error:** Render me `SITE_URL` daalo!")
        return

    markup = types.InlineKeyboardMarkup()
    # WebApp URL construction
    web_app_info = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Video Dekho (Click Here)", web_app=web_app_info))
    
    bot.reply_to(message, "👇 **Niche button dabakar Video dekho:**\n(Pura dekhne par hi paisa milega)", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    
    # Auto-Return Logic
    if len(message.text.split()) > 1 and message.text.split()[1].startswith("verified_"):
        amount = message.text.split("_")[1]
        bot.reply_to(message, f"✅ **Shabash!**\n\n💰 **+₹{amount}** jud gaye.", reply_markup=main_menu())
        return

    if not is_user_member(user_id):
        bot.reply_to(message, "⚠️ **Ruko!**\nBot use karne ke liye Channel join karna zaroori hai.", reply_markup=force_sub_markup())
        return
    
    get_user(user_id, message.from_user.username)
    
    # Referral Check
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id:
        referrer_id = int(args[1])
        user = get_user(user_id)
        if user['joined_via'] is None:
            update_user(user_id, {"joined_via": referrer_id})
            inc_balance(referrer_id, 40.0)
            inc_invites(referrer_id)
            try: bot.send_message(referrer_id, "🌟 **Badhai ho!** Referral Bonus: +₹40")
            except: pass

    bot.reply_to(message, "👋 **Namaste! MoneyTube me swagat hai.**\nAds dekho aur paise kamao! 💸", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def all_messages(message):
    user_id = message.chat.id
    if not is_user_member(user_id):
         bot.reply_to(message, "⚠️ **Channel Join Karo!**", reply_markup=force_sub_markup())
         return

    user = get_user(user_id)
    text = message.text
    
    if text == "💰 My Wallet":
        bot.reply_to(message, f"💳 **Aapka Wallet**\n\n💰 Balance: ₹{round(user['balance'], 2)}\n📺 Ads Watched: {user['ads_watched']}\n👥 Total Referrals: {user['invites']}")
        
    elif text == "🎁 Daily Bonus":
        today = str(date.today())
        if user.get('last_bonus') == today:
            time_left = get_time_remaining()
            bot.reply_to(message, f"❌ **Bonus le liya hai!**\n\n⏳ Agla Bonus: {time_left} baad aana.")
        else:
            bonus = round(random.uniform(10.00, 20.00), 2)
            inc_balance(user_id, bonus)
            update_user(user_id, {"last_bonus": today})
            bot.reply_to(message, f"🎁 **Daily Bonus Mil Gaya!**\n+₹{bonus} added.")

    elif text == "👥 Refer & Earn":
         ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
         bot.reply_to(message, f"📣 **Dosto ko Bulao!**\n\nHar friend par ₹40 milenge.\nLink: `{ref_link}`")

    elif text == "⚙️ Extra":
        bot.reply_to(message, "👇 **Other Options:**", reply_markup=extra_menu())

    elif text in ["🆘 Support", "❓ FAQ", "📢 Updates"]:
         if text == "🆘 Support": msg = f"📞 **Support:** @{os.environ.get('SUPPORT_USER', 'Admin')}"
         elif text == "📢 Updates": msg = f"📢 **Updates Channel:** {CHANNEL_LINK}"
         else: msg = "❓ **FAQ:**\n1. Play click karo\n2. 15 sec ruko\n3. Paisa kamao"
         bot.reply_to(message, msg)

    elif text == "🏦 Withdraw Money":
        bot.reply_to(message, "🏧 **Withdrawal Method Chuno:**", reply_markup=withdraw_menu())
        
    elif text == "🔙 Main Menu":
        bot.reply_to(message, "🏠 **Home**", reply_markup=main_menu())

    elif text in ["🇮🇳 UPI", "💳 Paytm", "🏦 Bank Transfer"]:
         # --- NEW SMART WITHDRAWAL LOGIC ---
         w_count = user.get('withdraw_count', 0)
         
         # Case 1: First Time Withdrawal (Easy)
         if w_count == 0:
             if user['balance'] < 10:
                 bot.reply_to(message, f"❌ **Balance Kam Hai!**\n\nPehli baar nikalne ke liye kam se kam **₹10** chahiye.\nAbhi hai: ₹{round(user['balance'], 2)}")
             else:
                 # Success
                 inc_withdraw_count(user_id) # Count badhao
                 bot.reply_to(message, "✅ **Request Submitted!**\n(First Withdrawal)\n\nAdmin check karke bhej denge.")
                 send_log(f"💸 **FIRST WITHDRAWAL** 💸\nUser: `{user_id}`\nAmount: ₹{round(user['balance'], 2)}\nMethod: {text}")

         # Case 2: Second Time Onwards (Hard)
         else:
             if user['balance'] < 300:
                  bot.reply_to(message, f"❌ **Minimum Withdraw: ₹300**\nAbhi Balance: ₹{round(user['balance'], 2)}")
             elif user['invites'] < 5:
                  bot.reply_to(message, f"❌ **Task Incomplete!**\n\nPaise nikalne ke liye **5 Doston** ko invite karna zaroori hai.\nAapke Invites: {user['invites']}/5")
             else:
                  inc_withdraw_count(user_id)
                  bot.reply_to(message, "✅ **Request Submitted!**\nAdmin jald hi process karenge.")
                  send_log(f"💸 **REGULAR WITHDRAWAL**\nUser: `{user_id}`\nAmount: ₹{round(user['balance'], 2)}\nMethod: {text}")

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("▶️ Ad Dekho", "💰 My Wallet", "🎁 Daily Bonus", "🏦 Withdraw Money", "👥 Refer & Earn", "⚙️ Extra")
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

# --- SERVER RUNNER ---
@server.route('/')
def home():
    return "✅ MoneyTube v1.9 (Bug Fix + Smart Withdraw) Running!"

def run_server():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    run_bot()
