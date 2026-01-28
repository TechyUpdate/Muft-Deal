# =====================  MONEYTUBE BOT  =====================
# Timer-only = 15-sec → auto reward → NO external SDK
# Copy-paste → GitHub → Render deploy → Done!

import os
import time
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
BOT_USERNAME = os.environ.get("BOT_USERNAME", "").replace("@", "")
SITE_URL     = os.environ.get("SITE_URL", "")
MONGO_URI    = os.environ.get("MONGO_URI", "")

# ---------- INIT ----------
app  = Flask(__name__)
bot  = telebot.TeleBot(TOKEN) if TOKEN else None
ad_sessions = {}          # user_id : start_time

if MONGO_URI:
    try:
        client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client['moneytube_db']
        users_col = db['users']
    except:
        db = None
else:
    db = None

# ---------- DB HELPERS ----------
def get_user(user_id, username=None):
    if not db: return {}
    user = users_col.find_one({"_id": user_id})
    if not user:
        user = {"_id": user_id, "balance": 0.0, "ads_watched": 0,
                "username": username, "joined_date": str(date.today())}
        users_col.insert_one(user)
    return user

def inc_balance(user_id, amount):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})

def inc_ads(user_id):
    if db: users_col.update_one({"_id": user_id}, {"$inc": {"ads_watched": 1}})

# ---------- FLASK ROUTES ----------
@app.route('/')
def home():
    return "✅ MoneyTube Bot Live!"

@app.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    if not user_id: return "Error: user_id missing", 400
    ad_sessions[user_id] = time.time()

    # Ultra-safe timer → 15-sec → auto redirect
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
        <title>MoneyTube</title>
        <style>
            body{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:#fff;font-family:Arial,Helvetica,sans-serif;text-align:center;height:100vh;margin:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
            .logo{font-size:48px;margin-bottom:10px}
            .title{font-size:24px;font-weight:bold;margin-bottom:30px;background:linear-gradient(90deg,#00c853,#00e676);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
            .timer{font-size:40px;color:#00c853;margin:20px 0}
            .status{font-size:16px;color:#aaa}
        </style>
    </head>
    <body>
        <div class="logo">📺</div>
        <div class="title">Watch & Earn</div>
        <div class="timer" id="timer">15</div>
        <div class="status" id="status">Please wait…</div>

        <script>
            const VERIFY_URL = \"""" + SITE_URL + """/verify?user_id=""" + user_id + """\";
            let left = 15;
            const timer = setInterval(()=>{
                left--; document.getElementById('timer').textContent=left;
                if(left<=0){
                    clearInterval(timer);
                    document.getElementById('status').textContent='✅ Done!';
                    setTimeout(()=>window.location.href=VERIFY_URL,500);
                }
            },1000);
        </script>
    </body>
    </html>
    """
    return html

@app.route('/verify')
def verify_task():
    user_id = request.args.get('user_id')
    if not user_id or user_id not in ad_sessions: return "❌ No session", 400
    if time.time() - ad_sessions[user_id] < 15: return "⏳ Wait more", 200
    try:
        uid = int(user_id)
        amt = round(random.uniform(3.0, 5.0), 2)
        inc_balance(uid, amt)
        inc_ads(uid)
        del ad_sessions[user_id]
        return redirect(f"tg://resolve?domain={BOT_USERNAME}&start=verified_{amt}")
    except: return "Error", 500

# ---------- BOT HANDLERS ----------
@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("verified_"):
        amt = args[1].split("_")[1]
        bot.reply_to(message, f"✅ *Bonus Received!*\n💰 *+₹{amt}*", parse_mode='Markdown')
        return
    get_user(message.chat.id, message.from_user.username)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🎬 Watch & Earn 🤑")
    markup.row("💼 My Account", "💸 Withdraw")
    markup.row("🎁 Daily Bonus", "🚀 Share & Earn")
    bot.reply_to(message, "👋 *Welcome to MoneyTube!*\n📺 Watch ads → earn ₹3-5 instantly.", parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎬 Watch & Earn 🤑")
def watch_ad(message):
    if not SITE_URL: return bot.reply_to(message, "❌ SITE_URL not set")
    user_id = message.chat.id
    markup  = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📺 Watch Video", web_app=types.WebAppInfo(f"{SITE_URL}/watch?user_id={user_id}")))
    bot.reply_to(message, "*Tap Play to start*\n💡 Watch full ad for ₹3-5 reward.", parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💼 My Account")
def my_account(message):
    u = get_user(message.chat.id)
    bot.reply_to(message, f"👤 *My Account*\n💰 Balance: ₹{u.get('balance',0)}\n📺 Ads: {u.get('ads_watched',0)}", parse_mode='Markdown')

# ---------- SERVER ----------
def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def run_bot():
    if bot: bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_server, daemon=True).start()
    run_bot()
