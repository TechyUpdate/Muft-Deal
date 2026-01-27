import os
import time
import random
from flask import Flask, request, redirect, jsonify
from threading import Thread
import telebot
from telebot import types
import pymongo
import certifi
from datetime import date

# ===== CONFIGURATION =====
TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MoneyTubeBot").replace("@", "")
AD_LINK = os.environ.get("AD_LINK", "https://google.com")
SITE_URL = os.environ.get("SITE_URL", "")
MONGO_URI = os.environ.get("MONGO_URI", "")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Telegram")

# ===== INIT =====
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN) if TOKEN else None
ad_sessions = {}  # user_id: start_timestamp

# MongoDB
if MONGO_URI:
    try:
        client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client['moneytube_db']
        users_col = db['users']
    except:
        db = None
else:
    db = None

# ===== DATABASE HELPERS =====
def get_user(user_id, username=None):
    if not db: return {}
    user = users_col.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id, "balance": 0.0, "invites": 0, "ads_watched": 0,
            "username": username, "joined_date": str(date.today())
        }
        users_col.insert_one(user)
    return user

def inc_balance(user_id, amount):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})

def inc_ads(user_id):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"ads_watched": 1}})

# ===== WEB ROUTES =====
@app.route('/')
def home():
    return "✅ MoneyTube Bot Running!"

@app.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    if not user_id:
        return "Error: User ID required", 400
    
    # Store session start time
    ad_sessions[user_id] = time.time()
    
    # Build ad link with tracking
    ad_link_with_tracking = f"{AD_LINK}?sub_id={user_id}&back_url={SITE_URL}/verify?user_id={user_id}"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>MoneyTube - Watch & Earn</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: white; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
                text-align: center; padding: 20px;
            }}
            .logo {{ font-size: 48px; margin-bottom: 10px; }}
            .title {{ font-size: 24px; font-weight: bold; margin-bottom: 30px;
                background: linear-gradient(90deg, #00c853, #00e676); -webkit-background-clip: text;
                -webkit-text-fill-color: transparent; }}
            .spinner {{ width: 60px; height: 60px; border: 4px solid #333; border-top: 4px solid #00c853;
                border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .status {{ font-size: 16px; color: #aaa; margin-bottom: 20px; }}
            .btn {{ background: #00c853; color: white; border: none; padding: 15px 40px;
                font-size: 18px; border-radius: 25px; cursor: pointer; margin-top: 20px; }}
            .hidden {{ display: none !important; }}
        </style>
    </head>
    <body>
        <div class="logo">📺</div>
        <div class="title">Watch & Earn</div>
        
        <div class="spinner" id="loader"></div>
        <div class="status" id="status">Opening ad in browser...</div>
        
        <button id="openBtn" class="btn hidden" onclick="openAd()">▶️ Open Ad</button>

        <script>
            const AD_LINK = "{ad_link_with_tracking}";
            const VERIFY_URL = "{SITE_URL}/verify?user_id={user_id}";
            let checkInterval;
            
            window.onload = function() {{
                if (window.Telegram?.WebApp) {{
                    window.Telegram.WebApp.ready();
                    window.Telegram.WebApp.expand();
                }}
                
                // Auto open after 1 second
                setTimeout(openAd, 1000);
            }};
            
            function openAd() {{
                document.getElementById('status').textContent = "Ad opening in browser...";
                
                // Open ad in external browser
                if (window.Telegram?.WebApp?.openLink) {{
                    window.Telegram.WebApp.openLink(AD_LINK);
                }} else {{
                    window.open(AD_LINK, '_system');
                }}
                
                // Start checking completion
                startChecking();
            }}
            
            function startChecking() {{
                // Poll every 2 seconds to check if enough time passed
                checkInterval = setInterval(async () => {{
                    const res = await fetch('{SITE_URL}/check-ad-status?user_id={user_id}');
                    const data = await res.json();
                    
                    if (data.completed) {{
                        clearInterval(checkInterval);
                        window.location.href = VERIFY_URL;
                    }}
                }}, 2000);
                
                // Fallback: Auto redirect after 25 seconds max
                setTimeout(() => {{
                    clearInterval(checkInterval);
                    window.location.href = VERIFY_URL;
                }}, 25000);
            }}
            
            // When user returns to this tab
            document.addEventListener('visibilitychange', () => {{
                if (!document.hidden) {{
                    fetch('{SITE_URL}/check-ad-status?user_id={user_id}')
                        .then(r => r.json())
                        .then(data => {{
                            if (data.completed) {{
                                window.location.href = VERIFY_URL;
                            }}
                        }});
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html

@app.route('/check-ad-status')
def check_ad_status():
    user_id = request.args.get('user_id')
    if not user_id or user_id not in ad_sessions:
        return jsonify({'completed': False})
    
    elapsed = time.time() - ad_sessions[user_id]
    return jsonify({'completed': elapsed >= 15})  # 15 seconds minimum

@app.route('/verify')
def verify_task():
    user_id = request.args.get('user_id')
    if not user_id or user_id not in ad_sessions:
        return "❌ Error: No active session", 400
    
    elapsed = time.time() - ad_sessions[user_id]
    if elapsed < 15:
        return "⏳ Please wait a bit more...", 200
    
    # Reward user
    try:
        uid = int(user_id)
        amount = round(random.uniform(3.00, 5.00), 2)
        
        inc_balance(uid, amount)
        inc_ads(uid)
        
        # Clean up
        del ad_sessions[user_id]
        
        return redirect(f"tg://resolve?domain={BOT_USERNAME}&start=verified_{amount}")
    except:
        return "Error processing reward", 500

# ===== BOT HANDLERS =====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    args = message.text.split()
    
    if len(args) > 1 and args[1].startswith("verified_"):
        amt = args[1].split("_")[1]
        bot.reply_to(message, f"✅ **Bonus Received!**\n💰 **+₹{amt}**", parse_mode='Markdown')
        return
    
    get_user(user_id, message.from_user.username)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🎬 Watch & Earn 🤑")
    markup.row("💼 My Account", "💸 Withdraw")
    markup.row("🎁 Daily Bonus", "🚀 Share & Earn")
    
    bot.reply_to(message, 
        "👋 **Welcome to MoneyTube!**\n\n" +
        "📺 Watch ads and earn real cash!\n" +
        "💰 Earn ₹3-5 per ad instantly",
        parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎬 Watch & Earn 🤑")
def watch_ad(message):
    if not SITE_URL:
        bot.reply_to(message, "❌ Error: SITE_URL not configured")
        return
    
    user_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")
    markup.add(types.InlineKeyboardButton("📺 Watch Video", web_app=web_app))
    
    bot.reply_to(message, 
        "**Click Play to start watching ad**\n\n" +
        "💡 Watch full ad to earn ₹3-5 instantly!",
        parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💼 My Account")
def my_account(message):
    user = get_user(message.chat.id)
    balance = user.get('balance', 0)
    ads = user.get('ads_watched', 0)
    
    bot.reply_to(message,
        f"👤 **My Account**\n\n" +
        f"💰 Balance: ₹{balance}\n" +
        f"📺 Ads Watched: {ads}\n" +
        f"🆔 User ID: `{message.chat.id}`",
        parse_mode='Markdown')

# ===== SERVER START =====
def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def run_bot():
    if bot:
        bot.infinity_polling()

if __name__ == "__main__":
    # Start Flask in thread
    server_thread = Thread(target=run_server)
    server_thread.start()
    
    # Start bot
    if bot:
        run_bot()
    else:
        print("⚠️ Bot token not found, running web server only")
