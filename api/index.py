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
OWNER_ID = int(os.environ.get("OWNER_ID", "8088024998"))

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
PENDING_ANNOUNCEMENTS = {}
LAST_SENT_ANIME = ""

# --- DATABASE & CHAT FUNCTIONS ---
DB_FILE = "jarvis_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY, chat_type TEXT)')
    conn.commit()
    conn.close()

init_db()

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

# --- IMPROVED DYNAMIC NEWS GENERATOR WITH CONDITIONAL DATES ---
def fetch_latest_anime_news():
    current_time, current_date = get_current_ist_datetime()
    
    if GROQ_API_KEY:
        try:
            topics = ["New Anime Season Release", "Trending Manga Adaptation", "Upcoming Movie Release", "Studio Announcement"]
            topic = random.choice(topics)
            
            prompt = (
                f"Write a short, exciting Telegram announcement about a *random* anime update regarding: {topic}. "
                "DO NOT mention Demon Slayer. Pick popular anime like Oshi no Ko, Chainsaw Man, JJK, Solo Leveling, or new 2026/2027 anime announcements. "
                "CRITICAL RELEASE DATE RULE:\n"
                "- If an exact release date is known, write: '📅 Release Date: <Exact Date>'\n"
                "- If no exact date is confirmed, DO NOT leave it blank and DO NOT write 'No date'. Instead write: '📅 Expected Release: <Season/Year e.g. Fall 2026 or Early 2027>'\n\n"
                "Format with:\n"
                "📌 Title\n"
                "📅 Release Date / Expected Release (Follow the rule above strictly)\n"
                "🎬 Status / Studio\n"
                "📝 Short Synopsis\n\n"
                "Use clean markdown with emojis."
            )
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.85
            }
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                ai_text = res.json()['choices'][0]['message']['content']
                return (
                    f"{ai_text}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🕒 **Update Fetched:** `{current_date}` at `{current_time} IST`"
                )
        except Exception as e:
            logging.error(f"AI Generator Error: {e}")

    return (
        f"🚨 **NEW ANIME ANNOUNCEMENT** 🚨\n\n"
        f"📌 **Title:** `Jujutsu Kaisen Season 3`\n"
        f"📅 **Expected Release:** `Late 2026`\n"
        f"🎬 **Status:** `Production Confirmed`\n\n"
        f"📝 **Synopsis:** The Culling Game arc adaptation enters full production pipeline.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 **Update Fetched:** `{current_date}` at `{current_time} IST`"
    )

# --- AUTO-SCHEDULER ---
def start_auto_anime_scheduler():
    def scheduler_loop():
        global LAST_SENT_ANIME
        while True:
            try:
                anime_text = fetch_latest_anime_news()
                if "Demon Slayer" not in anime_text:
                    LAST_SENT_ANIME = anime_text
                    post_id = str(random.randint(1000, 9999))
                    PENDING_ANNOUNCEMENTS[post_id] = anime_text

                    markup = InlineKeyboardMarkup()
                    markup.row(
                        InlineKeyboardButton("✅ Approve & Broadcast", callback_data=f"approve_{post_id}"),
                        InlineKeyboardButton("❌ Cancel", callback_data=f"reject_{post_id}")
                    )
                    bot.send_message(OWNER_ID, format_text(f"🔔 **NEW ANIME UPDATE!**\n\n{anime_text}\n\n👇 Post karein?"), reply_markup=markup, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Scheduler Error: {e}")
            
            time.sleep(21600) # Check every 6 hours

    t = Thread(target=scheduler_loop)
    t.daemon = True
    t.start()

# --- HANDLERS ---
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

if __name__ == "__main__":
    keep_alive()
    start_auto_anime_scheduler()
    bot.infinity_polling(allowed_updates=['message', 'callback_query', 'channel_post'])
