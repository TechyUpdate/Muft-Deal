import os
import random
from flask import Flask, request, redirect
from threading import Thread
import telebot
from telebot import types
import pymongo
import certifi
from datetime import date

# ---------- CONFIG ----------
TOKEN        = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MoneyTubeBot").replace("@", "")
SITE_URL     = os.environ.get("SITE_URL", "") # https://tumarasite.onrender.com
MONGO_URI    = os.environ.get("MONGO_URI", "")

# ---------- INIT ----------
app  = Flask(__name__)
bot  = telebot.TeleBot(TOKEN) if TOKEN else None
ad_sessions = {}

if MONGO_URI:
    try:
        client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client['moneytube_db']
        users_col = db['users']
    except:
        db = None
else:
    db = None

# ---------- DB HELPERS (Same as before) ----------
def get_user(user_id, username=None):
    if not db: return {}
    user = users_col.find_one({"_id": user_id})
    if not user:
        user = {"_id": user_id, "balance": 0.0, "ads_watched": 0, "username": username}
        users_col.insert_one(user)
    return user

def inc_balance(user_id, amount):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})

def inc_ads(user_id):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"ads_watched": 1}})

# ---------- FLASK ROUTES ----------
@app.route('/')
def home():
    return "✅ SDK Bot Running..."

@app.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    
    # ⚠️ 1. YAHAN "COPY THIS TAG" WALA CODE DALNA HAI
    # (Monetag Dashboard se 'Installation' wala code copy karke yahan paste karo)
    # Example: <script src="//thubr.com/sdk.js" data-zone="12345" data-sdk="show_12345"></script>
    SDK_SCRIPT_TAG = """
    <script src="//libtl.com/sdk.js" data-zone="YOUR_ZONE_ID" data-sdk="show_YOUR_ZONE_ID"></script> 
    """

    # ⚠️ 2. YAHAN "REWARDED INTERSTITIAL" WALA FUNCTION NAME DALNA HAI
    # (Sirf function ka naam, jaise 'show_848484')
    AD_FUNCTION_NAME = "show_848484" # <-- Ise change karke apna wala likho

        # === YAHAN SE COPY KARO ===
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Watch & Earn</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        
        <script src='//libtl.com/sdk.js' data-zone='10452164' data-sdk='show_10452164'></script>
        
        <style>
            body {{ background-color: #000; color: white; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
            .btn {{ padding: 15px 30px; font-size: 20px; background: #00e676; color: #000; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; margin-top: 20px; }}
            p {{ color: #aaa; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <h2>💰 Watch Ad to Earn</h2>
        
        <button class="btn" onclick="showAd()">📺 Watch Video</button>
        <p id="status">Tap button to start...</p>

        <script>
            const verifyLink = '{SITE_URL}/verify?user_id={user_id}';

            function showAd() {{
                document.getElementById('status').innerText = "Loading Ad...";
                
                // ✅ TERA FUNCTION NAME (show_10452164) YAHAN LAGA DIYA HAI
                if (typeof show_10452164 === 'function') {{
                    
                    show_10452164().then(() => {{
                        document.getElementById('status').innerText = "✅ Success!";
                        // Ad khatam hone ke baad redirect
                        window.location.href = verifyLink;
                    }});
                    
                }} else {{
                    alert("Ad Script load nahi hui. Internet check karein.");
                }}
            }}
            
            // Auto Expand
            window.onload = function() {{
                if(window.Telegram && window.Telegram.WebApp) {{
                    window.Telegram.WebApp.expand();
                }}
            }}
        </script>
    </body>
    </html>
    """
    return html

@app.route('/verify')
def verify_task():
    user_id = request.args.get('user_id')
    try:
        uid = int(user_id)
        amt = round(random.uniform(4.0, 8.0), 2)
        inc_balance(uid, amt)
        inc_ads(uid)
        return redirect(f"tg://resolve?domain={BOT_USERNAME}&start=verified_{amt}")
    except:
        return "Error"

# ---------- BOT LOGIC (Same) ----------
@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("verified_"):
        amt = args[1].split("_")[1]
        bot.reply_to(message, f"✅ *Reward Received!*\n💰 *+₹{amt}*", parse_mode='Markdown')
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📺 Watch Video", web_app=types.WebAppInfo(f"{SITE_URL}/watch?user_id={message.chat.id}")))
    bot.reply_to(message, "👇 *Click below to Earn*", reply_markup=markup)

# ---------- SERVER ----------
def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    Thread(target=run_server, daemon=True).start()
    if bot: bot.infinity_polling()
