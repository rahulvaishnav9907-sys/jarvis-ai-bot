import os
import logging
import asyncio
import datetime
import random
import time
import pytz
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from threading import Thread
from flask import Flask

logging.basicConfig(level=logging.INFO)

app = Flask('')

@app.route('/')
def home():
    return "J.A.R.V.I.S. Core Engine Active!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
SUPPORT_BOT_TOKEN = os.environ.get("SUPPORT_BOT_TOKEN", "").strip()

try:
    OWNER_ID = int(os.environ.get("OWNER_ID", "8088024998"))
except ValueError:
    OWNER_ID = 8088024998

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
PENDING_ANNOUNCEMENTS = {}

# --- DEEP DATABASE SETUP & HISTORY TRACKING ---
DB_FILE = "jarvis_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            language_code TEXT,
            is_premium INTEGER,
            chat_type TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_type TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_anime_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_title TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def record_sent_anime(title):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sent_anime_history (anime_title) VALUES (?)", (str(title),))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Sent Anime Record Error: {e}")

def get_recent_sent_titles():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT anime_title FROM sent_anime_history ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []

def save_and_notify_user(user, chat_type):
    try:
        if not user or not hasattr(user, 'id'):
            return
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user.id,))
        exists = cursor.fetchone()

        first_name = user.first_name or "N/A"
        last_name = user.last_name or "N/A"
        username = f"@{user.username}" if user.username else "No Username"
        lang = getattr(user, 'language_code', None) or "Unknown"
        is_premium = 1 if getattr(user, 'is_premium', False) else 0

        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, first_name, last_name, username, language_code, is_premium, chat_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user.id, first_name, last_name, username, lang, is_premium, str(chat_type)))
        
        cursor.execute("INSERT OR IGNORE INTO chats (chat_id, chat_type) VALUES (?, ?)", (user.id, str(chat_type)))
        conn.commit()
        conn.close()

        if not exists and user.id != OWNER_ID:
            ist = pytz.timezone('Asia/Kolkata')
            now_time = datetime.datetime.now(ist).strftime("%d %b %Y, %I:%M %p")
            premium_status = "⭐ Premium User" if is_premium else "👤 Regular User"
            
            alert_msg = (
                f"🚨 **NEW USER REGISTERED ON BOT!**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 **Name:** {first_name} {last_name if last_name != 'N/A' else ''}\n"
                f"🆔 **User ID:** `{user.id}`\n"
                f"🔗 **Username:** {username}\n"
                f"🌐 **Language:** `{lang}`\n"
                f"💎 **Account Type:** {premium_status}\n"
                f"💬 **Joined Via:** `{chat_type}`\n"
                f"🕒 **Time:** `{now_time} IST`"
            )
            bot.send_message(OWNER_ID, alert_msg, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"User Save Error: {e}")

def get_all_detailed_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, first_name, username, language_code, registered_at FROM users")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_chats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, chat_type FROM chats")
    rows = cursor.fetchall()
    conn.close()
    return rows

def format_text(text):
    if "⚡ Powered by - Anime Nation" not in text:
        return f"{text.strip()}\n\n⚡ *Powered by - Anime Nation*"
    return text.strip()

def get_current_ist_datetime():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)
    return now.strftime("%I:%M %p"), now.strftime("%B %d, %Y")

# --- DYNAMIC NEWS GENERATOR ---
def fetch_latest_anime_news():
    current_time, current_date = get_current_ist_datetime()
    recent_sent = get_recent_sent_titles()
    recent_str = ", ".join(recent_sent) if recent_sent else "None"
    
    if GROQ_API_KEY:
        try:
            anime_pool = [
                "Chainsaw Man Season 2 / Reze Arc Movie",
                "Jujutsu Kaisen Season 3 (Culling Game)",
                "Solo Leveling Season 2 / Arise from the Shadows",
                "Blue Lock Season 2 / U-20 Arc",
                "Kaiju No. 8 Season 2",
                "Bleach: Thousand-Year Blood War Part 3",
                "One Piece Remake / WIT Studio Project",
                "Hell's Paradise Season 2",
                "Black Clover New Season / Anime Return",
                "My Hero Academia Final Season",
                "Spy x Family Season 3",
                "Classroom of the Elite Season 4"
            ]
            
            available_pool = [a for a in anime_pool if not any(r.lower() in a.lower() for r in recent_sent)]
            selected_topic = random.choice(available_pool if available_pool else anime_pool)
            
            prompt = (
                f"Write a short, exciting Telegram announcement about an upcoming or newly announced anime project: '{selected_topic}'.\n\n"
                f"STRICT DUPLICATE PREVENTION RULE:\n"
                f"DO NOT write about these recently covered anime: [{recent_str}, Demon Slayer, Oshi no Ko].\n\n"
                f"RELEASE DATE RULE:\n"
                f"- If exact date is known, write: '📅 Release Date: <Exact Date>'\n"
                f"- If no exact date, write: '📅 Expected Release: <Season/Year e.g. Fall 2026 or Early 2027>'\n\n"
                f"Format with clean Markdown:\n"
                f"📌 Title\n"
                f"📅 Release Date / Expected Release\n"
                f"🎬 Studio / Production Status\n"
                f"📝 Short Synopsis & Hype Summary\n"
            )
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.95
            }
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                ai_text = res.json()['choices'][0]['message']['content']
                record_sent_anime(selected_topic)
                return (
                    f"{ai_text}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🕒 **Update Fetched:** `{current_date}` at `{current_time} IST`"
                )
        except Exception as e:
            logging.error(f"AI Generator Error: {e}")

    fallback_title = f"Chainsaw Man: Reze Arc Movie / Season 2 ({random.randint(100, 999)})"
    record_sent_anime(fallback_title)
    return (
        f"🚨 **NEW ANIME ANNOUNCEMENT** 🚨\n\n"
        f"📌 **Title:** `{fallback_title}`\n"
        f"📅 **Expected Release:** `Late 2026`\n"
        f"🎬 **Studio:** `MAPPA`\n\n"
        f"📝 **Synopsis:** Official production and global theatrical release schedule updated.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 **Update Fetched:** `{current_date}` at `{current_time} IST`"
    )

# --- AUTO-SCHEDULER ---
def start_auto_anime_scheduler():
    def scheduler_loop():
        while True:
            try:
                anime_text = fetch_latest_anime_news()
                post_id = str(random.randint(1000, 9999))
                PENDING_ANNOUNCEMENTS[post_id] = anime_text

                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("✅ Approve & Broadcast", callback_data=f"approve_{post_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"reject_{post_id}")
                )
                bot.send_message(OWNER_ID, format_text(f"🔔 **NEW UNIQUE ANIME UPDATE!**\n\n{anime_text}\n\n👇 Post karein?"), reply_markup=markup, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Scheduler Error: {e}")
            
            time.sleep(21600)

    t = Thread(target=scheduler_loop)
    t.daemon = True
    t.start()

# --- COMMANDS ---
@bot.message_handler(commands=['all_users', 'allusers'])
def all_users_cmd(message):
    save_and_notify_user(message.from_user, message.chat.type)
    if message.from_user.id != OWNER_ID:
        return

    users = get_all_detailed_users()
    if not users:
        bot.reply_to(message, "⚠️ Koi users database mein nahi mile.")
        return

    msg = f"👥 **REGISTERED USER LIST ({len(users)} Total):**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for idx, u in enumerate(users, 1):
        u_id, name, username, lang, reg_date = u
        msg += f"{idx}. **{name}** ({username})\n   • ID: `{u_id}` | Lang: `{lang}`\n   • Date: `{reg_date}`\n\n"
        if len(msg) > 3500:
            bot.send_message(OWNER_ID, msg, parse_mode="Markdown")
            msg = ""

    if msg:
        bot.send_message(OWNER_ID, msg, parse_mode="Markdown")

@bot.message_handler(commands=['user_info'])
def user_info_cmd(message):
    save_and_notify_user(message.from_user, message.chat.type)
    if message.from_user.id != OWNER_ID:
        return

    args = message.text.split()
    if len(args) < 2 or args[1] == "<user_id>":
        bot.reply_to(message, "⚠️ Format: `/user_info 8088024998` (असली User ID लिखें)", parse_mode="Markdown")
        return

    target_id = args[1]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (target_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        bot.reply_to(message, f"❌ User ID `{target_id}` database mein nahi mila.", parse_mode="Markdown")
        return

    u_id, fname, lname, uname, lang, is_prem, ctype, reg_time = user
    info_msg = (
        f"🔍 **DEEP USER PROFILE DATA**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 **First Name:** {fname}\n"
        f"👤 **Last Name:** {lname}\n"
        f"🆔 **User ID:** `{u_id}`\n"
        f"🔗 **Username:** {uname}\n"
        f"🌐 **Language:** `{lang}`\n"
        f"⭐ **Premium Status:** `{'Yes' if is_prem else 'No'}`\n"
        f"💬 **Chat Type:** `{ctype}`\n"
        f"📅 **Registered At:** `{reg_time}`"
    )
    bot.reply_to(message, info_msg, parse_mode="Markdown")

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    save_and_notify_user(message.from_user, message.chat.type)
    user_name = message.from_user.first_name or "User"
    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, format_text(f"👑 **WELCOME OWNER!**\n\nCommands:\n• `/all_users` : Full Users List\n• `/user_info <id>` : User Details\n• `/fetch_anime` : Fetch Anime News"), parse_mode="Markdown")
        return
    bot.reply_to(message, format_text(f"🤖 **Hello {user_name}! Main J.A.R.V.I.S. hoon — aapka personal AI assistant.**"), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def handle_approval_click(call):
    action, post_id = call.data.split('_')
    if action == "approve":
        anime_text = PENDING_ANNOUNCEMENTS.get(post_id)
        if anime_text:
            all_chats = get_all_chats()
            success = 0
            for chat_id, _ in all_chats:
                try: 
                    bot.send_message(chat_id, format_text(anime_text), parse_mode="Markdown")
                    success += 1
                except: pass
            bot.edit_message_text(f"✅ **BROADCASTED!** Sent to `{success}` chats.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            PENDING_ANNOUNCEMENTS.pop(post_id, None)
    else:
        bot.edit_message_text("❌ **CANCELLED.**", chat_id=call.message.chat.id, message_id=call.message.message_id)
        PENDING_ANNOUNCEMENTS.pop(post_id, None)

@bot.message_handler(commands=['fetch_anime'])
def manual_fetch(message):
    save_and_notify_user(message.from_user, message.chat.type)
    if message.from_user.id != OWNER_ID: return
    bot.send_chat_action(message.chat.id, 'typing')
    anime_text = fetch_latest_anime_news()
    post_id = str(random.randint(1000, 9999))
    PENDING_ANNOUNCEMENTS[post_id] = anime_text
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Approve & Broadcast", callback_data=f"approve_{post_id}"), 
        InlineKeyboardButton("❌ Cancel", callback_data=f"reject_{post_id}")
    )
    bot.send_message(OWNER_ID, format_text(f"🔔 **MANUAL FETCH:**\n\n{anime_text}\n\n👇 Post karein?"), reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def track_and_reply(message):
    save_and_notify_user(message.from_user, message.chat.type)

if __name__ == "__main__":
    keep_alive()
    start_auto_anime_scheduler()
    bot.infinity_polling(allowed_updates=['message', 'callback_query', 'channel_post'])
    
