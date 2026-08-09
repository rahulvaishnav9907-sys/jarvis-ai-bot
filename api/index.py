import os
import logging
import asyncio
import datetime
import random
import pytz
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import edge_tts
import sqlite3
import html
from threading import Thread
from flask import Flask

logging.basicConfig(level=logging.INFO)

# --- FLASK SERVER FOR RENDER PORT BINDING ---
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

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
SUPPORT_BOT_TOKEN = os.environ.get("SUPPORT_BOT_TOKEN", "").strip()

FOOTER_TEXT = "⚡ *Powered by - Anime Nation*"

try:
    OWNER_ID = int(os.environ.get("OWNER_ID", "8088024998"))
except ValueError:
    OWNER_ID = 8088024998

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

BOT_USERNAME = ""
try:
    bot_info = bot.get_me()
    BOT_USERNAME = bot_info.username.lower()
except Exception as e:
    logging.error(f"Failed to fetch bot username: {e}")

PENDING_ANNOUNCEMENTS = {}

# --- DATABASE SETUP ---
DB_FILE = "jarvis_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_type TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def register_chat(chat_id, chat_type="private"):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO chats (chat_id, chat_type) VALUES (?, ?)", (chat_id, str(chat_type)))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DB Error: {e}")

def record_quiz_play(chat_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO quiz_stats (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Quiz Stat Save Error: {e}")

def get_quiz_total_played():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM quiz_stats")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def save_memory(chat_id, role, content):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO memory (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, role, content))
        cursor.execute('''
            DELETE FROM memory 
            WHERE chat_id = ? AND id NOT IN (
                SELECT id FROM memory WHERE chat_id = ? ORDER BY id DESC LIMIT 10
            )
        ''', (chat_id, chat_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Memory Save Error: {e}")

def get_chat_history(chat_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM memory WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r[0], "content": r[1]} for r in rows]
    except Exception:
        return []

def get_chat_metrics():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chats")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chats WHERE chat_type = 'private'")
        users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chats WHERE chat_type IN ('group', 'supergroup')")
        groups = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chats WHERE chat_type = 'channel'")
        channels = cursor.fetchone()[0]
        conn.close()
        return total, users, groups, channels
    except Exception:
        return 0, 0, 0, 0

def get_all_chats():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, chat_type FROM chats")
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception:
        return []

def format_text(text):
    if "Powered by - Anime Nation" not in text:
        return f"{text.strip()}\n\n{FOOTER_TEXT}"
    return text.strip()

def get_current_ist_datetime():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)
    return now.strftime("%I:%M %p"), now.strftime("%B %d, %Y")

# --- HIGH QUALITY ANIME UPDATE GENERATOR WITH DATE & TIME ---
def fetch_latest_anime_news():
    current_time, current_date = get_current_ist_datetime()
    
    url = "https://api.jikan.moe/v4/seasons/upcoming"
    try:
        res = requests.get(url, timeout=6).json()
        if res.get('data'):
            anime_list = res['data']
            selected = random.choice(anime_list[:15])
            title = selected.get('title', 'Unknown Anime')
            synopsis = selected.get('synopsis', 'Synopsis unavailable.')
            if synopsis and len(synopsis) > 220:
                synopsis = synopsis[:220] + "..."
            
            season = selected.get('season', 'Upcoming')
            year = selected.get('year', '2026/2027')
            episodes = selected.get('episodes', 'TBA')
            
            return (
                f"🚨 **NEW ANIME ANNOUNCEMENT** 🚨\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Title:** `{title}`\n"
                f"🗓️ **Release Period:** `{season.capitalize()} {year}`\n"
                f"🎬 **Episodes:** `{episodes}`\n\n"
                f"📝 **Synopsis:**\n{synopsis}\n\n"
                f"🕒 **Update Fetched:** `{current_date}` at `{current_time} IST`"
            )
    except Exception as e:
        logging.error(f"API Error: {e}")

    # High quality fallback with date/time
    return (
        f"🚨 **NEW ANIME ANNOUNCEMENT** 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 **Title:** `Demon Slayer: Kimetsu no Yaiba - Next Chapter`\n"
        f"🗓️ **Release Period:** `Late 2026 / Early 2027`\n"
        f"🎬 **Status:** `Official Production Active`\n\n"
        f"📝 **Synopsis:**\nOfficial production and global premiere schedule updated for upcoming anime projects.\n\n"
        f"🕒 **Update Fetched:** `{current_date}` at `{current_time} IST`"
    )

# --- HIGH-LEVEL INTELLIGENCE ENGINE ---
def get_groq_response(chat_id, prompt_text, user_name="Boss"):
    if not GROQ_API_KEY:
        return "GROQ_API_KEY environment variable missing hai."
    
    current_time, current_date = get_current_ist_datetime()
    history = get_chat_history(chat_id)

    system_instruction = {
        "role": "system",
        "content": (
            f"You are J.A.R.V.I.S., an advanced AI assistant created and owned strictly by 'Anime Nation'. "
            f"You are talking to '{user_name}'.\n"
            f"STRICT RULES:\n"
            f"1. Your Owner/Creator is strictly 'Anime Nation'. Never mention Tony Stark or Iron Man.\n"
            f"2. Be direct, clear, highly intelligent, and natural.\n"
            f"3. Real-time context: Time = {current_time} IST, Date = {current_date}.\n"
            f"4. Do NOT use markdown headers like '#' or '##'. Use bold text and clean bullet points."
        )
    }

    messages = [system_instruction] + history + [{"role": "user", "content": prompt_text}]

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 2048,
        "top_p": 0.95
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content']
            save_memory(chat_id, "user", prompt_text)
            save_memory(chat_id, "assistant", reply)
            return reply
    except Exception as e:
        logging.error(f"Groq AI Error: {e}")
    return "Neural system mein temporary delay aaya hai. Please retry."

# --- CHANNEL POST TRACKER ---
@bot.channel_post_handler(func=lambda message: True)
def track_channel_posts(message):
    register_chat(message.chat.id, "channel")

@bot.my_chat_member_handler()
def track_my_status(message):
    register_chat(message.chat.id, message.chat.type)

# --- ANIME UPDATE FETCH & APPROVAL SYSTEM ---
@bot.message_handler(commands=['fetch_anime'])
def fetch_anime_approval(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, format_text("⚠️ Access Denied: Authorized for Owner only."), parse_mode="Markdown")
        return

    bot.send_chat_action(message.chat.id, 'typing')
    anime_text = fetch_latest_anime_news()
    post_id = str(random.randint(1000, 9999))
    PENDING_ANNOUNCEMENTS[post_id] = anime_text

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Approve & Broadcast", callback_data=f"approve_{post_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"reject_{post_id}")
    )

    review_msg = (
        f"📋 **NEW ANIME ANNOUNCEMENT FOR REVIEW**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{anime_text}\n\n"
        f"👇 **Boss, kya ise channels/groups mein post karein?**"
    )
    bot.send_message(OWNER_ID, format_text(review_msg), reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def handle_approval_click(call):
    action, post_id = call.data.split('_')
    
    if action == "approve":
        anime_text = PENDING_ANNOUNCEMENTS.get(post_id)
        if not anime_text:
            bot.answer_callback_query(call.id, "⚠️ Announcement not found or expired.", show_alert=True)
            return

        all_chats = get_all_chats()
        success = 0
        for chat_id, chat_type in all_chats:
            try:
                bot.send_message(chat_id, format_text(anime_text), parse_mode="Markdown")
                success += 1
            except Exception:
                pass

        bot.edit_message_text(
            f"✅ **APPROVED & BROADCASTED!**\nSent to `{success}` channels/groups.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        PENDING_ANNOUNCEMENTS.pop(post_id, None)

    elif action == "reject":
        bot.edit_message_text(
            "❌ **ANNOUNCEMENT CANCELLED.**",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        PENDING_ANNOUNCEMENTS.pop(post_id, None)

# --- OTHER COMMANDS ---
@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    register_chat(message.chat.id, message.chat.type)
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"

    if user_id == OWNER_ID:
        total_chats, users_count, groups_count, channels_count = get_chat_metrics()
        owner_dashboard = (
            f"👑 **OWNER CONTROL PANEL**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Welcome back, Boss ({user_name})!\n\n"
            f"🛠️ **COMMANDS:**\n"
            f"• `/fetch_anime` : Fetch latest Anime News for Review\n"
            f"• `/broadcast <msg>` : Global Broadcast\n"
            f"• `/stats` : System Analytics\n"
            f"• `/quiz` : Anime Quiz"
        )
        bot.reply_to(message, format_text(owner_dashboard), parse_mode="Markdown")
        return

    msg_1 = f"🤖 **Hello {user_name}! Main J.A.R.V.I.S. hoon — aapka personal AI assistant.**"
    bot.reply_to(message, format_text(msg_1), parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    total_chats, users_count, groups_count, channels_count = get_chat_metrics()
    bot.reply_to(message, format_text(f"📊 **TOTAL USERS:** `{users_count}` | **CHANNELS/GROUPS:** `{groups_count + channels_count}`"), parse_mode="Markdown")

# --- MAIN AI CHAT HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    register_chat(message.chat.id, message.chat.type)
    user_name = message.from_user.first_name or "User"
    
    if message.chat.type in ['group', 'supergroup']:
        is_reply_to_bot = (
            message.reply_to_message is not None and 
            message.reply_to_message.from_user is not None and 
            message.reply_to_message.from_user.id == bot.get_me().id
        )
        is_bot_mentioned = (BOT_USERNAME != "" and BOT_USERNAME in message.text.lower())
        if not (is_reply_to_bot or is_bot_mentioned):
            return

    clean_prompt = message.text
    if BOT_USERNAME and f"@{BOT_USERNAME}" in clean_prompt.lower():
        clean_prompt = clean_prompt.lower().replace(f"@{BOT_USERNAME}", "").strip()

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_groq_response(message.chat.id, clean_prompt, user_name=user_name)
        bot.reply_to(message, format_text(ai_reply), parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, format_text(f"System Error: `{e}`"), parse_mode="Markdown")

if __name__ == "__main__":
    keep_alive()
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    bot.infinity_polling(timeout=10, long_polling_timeout=5, allowed_updates=['message', 'my_chat_member', 'channel_post', 'callback_query'])
