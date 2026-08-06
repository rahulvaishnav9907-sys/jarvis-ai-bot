import os
import json
import logging
import urllib.parse
import asyncio
import datetime
import pytz
import requests
import telebot
import edge_tts
import sqlite3

logging.basicConfig(level=logging.INFO)

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
SUPPORT_BOT_TOKEN = os.environ.get("SUPPORT_BOT_TOKEN", "").strip()

FOOTER = "\n\n⚡ *Powered by - Anime Nation*"

try:
    OWNER_ID = int(os.environ.get("OWNER_ID", "8088024998"))
except ValueError:
    OWNER_ID = 8088024998

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Database Setup for Lifetime User Tracking
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
    conn.commit()
    conn.close()

init_db()

def register_chat(chat_id, chat_type="private"):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO chats (chat_id, chat_type) VALUES (?, ?)", (chat_id, chat_type))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DB Error: {e}")

def get_total_chats():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chats")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def get_all_chat_ids():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM chats")
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []

# Real-time IST Time & Date Generator
def get_current_ist_datetime():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)
    current_time = now.strftime("%I:%M %p")
    current_date = now.strftime("%A, %B %d, %Y")
    return current_time, current_date

def get_groq_response(prompt_text, user_name="Sir"):
    if not GROQ_API_KEY:
        return "Sir, GROQ_API_KEY environment variable mein missing hai."
    
    current_time, current_date = get_current_ist_datetime()
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"You are J.A.R.V.I.S., an intelligent and witty AI assistant. "
                    f"Always address the user by their name '{user_name}'. "
                    f"Real-time Current IST Time: {current_time}. "
                    f"Real-time Current Date: {current_date}. "
                    f"Whenever asked about time, date, or day, use this real-time info. "
                    f"Respond concisely in character."
                )
            },
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"Groq API Error: {e}")
    return "Sir, core intelligence access karte waqt problem hui hai."

@bot.my_chat_member_handler()
def track_chats(message):
    register_chat(message.chat.id, message.chat.type)

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    register_chat(message.chat.id, message.chat.type)
    user_name = message.from_user.first_name or "User"
    welcome_text = (
        f"🤖 **J.A.R.V.I.S. ONLINE (Render Active)**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Good day, {user_name}! All systems operational.\n\n"
        f"📊 **Commands:**\n"
        f"• `/support_status` : Support Bot status check\n"
        f"• `/v <message>` : Voice mode chat (Deep Voice)\n"
        f"• `/broadcast <msg>` : Mass broadcast to all chats\n"
        f"• `/stats` : Check Total Users & System Metrics\n"
        f"• `/owner` : Owner Access Check"
        f"{FOOTER}"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['stats', 'users'])
def stats_cmd(message):
    register_chat(message.chat.id, message.chat.type)
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, f"⚠️ Access Denied: Sirf Boss hi stats check kar sakte hain.{FOOTER}", parse_mode="Markdown")
        return

    bot.reply_to(message, "🔄 *Fetching system metrics...*", parse_mode="Markdown")

    total_users = get_total_chats()
    
    support_status_text = "🔴 Offline / Unknown"
    support_username = "@TEAMNATI0Nbot"
    
    if SUPPORT_BOT_TOKEN:
        try:
            url = f"https://api.telegram.org/bot{SUPPORT_BOT_TOKEN}/getMe"
            res = requests.get(url, timeout=5).json()
            if res.get("ok"):
                support_status_text = f"🟢 Active ({res['result']['first_name']})"
                support_username = f"@{res['result']['username']}"
        except Exception:
            support_status_text = "🔴 Unreachable"

    current_time, current_date = get_current_ist_datetime()

    stats_msg = (
        f"📊 **SYSTEM METRICS REPORT**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 **J.A.R.V.I.S. AI BOT**\n"
        f"• **Total Users & Joined Chats:** `{total_users}`\n"
        f"• **Status:** 🟢 Online & Running\n\n"
        f"🎧 **SUPPORT BOT ({support_username})**\n"
        f"• **Status:** {support_status_text}\n\n"
        f"🕒 **SYSTEM TIME (IST):** `{current_time}`\n"
        f"📅 **SYSTEM DATE:** `{current_date}`"
        f"{FOOTER}"
    )
    
    bot.reply_to(message, stats_msg, parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, f"⚠️ Access Denied: Sirf Boss hi broadcast kar sakte hain.{FOOTER}", parse_mode="Markdown")
        return

    broadcast_msg = message.text.replace('/broadcast', '').strip()
    if not broadcast_msg:
        bot.reply_to(message, f"⚠️ Command format: `/broadcast Aapka Message Here`{FOOTER}", parse_mode="Markdown")
        return

    bot.reply_to(message, "📢 *Initiating Global Broadcast across all Groups & Channels...*", parse_mode="Markdown")
    
    all_chat_ids = get_all_chat_ids()
    success = 0
    failed = 0

    for chat_id in all_chat_ids:
        try:
            bot.send_message(
                chat_id, 
                f"📢 **J.A.R.V.I.S. BROADCAST ANNOUNCEMENT**\n━━━━━━━━━━━━━━━━━━━━━━\n\n{broadcast_msg}{FOOTER}",
                parse_mode="Markdown"
            )
            success += 1
        except Exception:
            failed += 1

    report = (
        f"📊 **BROADCAST REPORT COMPLETE**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 **Successfully Delivered:** `{success}` chats\n"
        f"🔴 **Failed / Removed:** `{failed}` chats"
        f"{FOOTER}"
    )
    bot.reply_to(message, report, parse_mode="Markdown")

@bot.message_handler(commands=['support_status'])
def check_support_status(message):
    register_chat(message.chat.id, message.chat.type)
    if not SUPPORT_BOT_TOKEN:
        bot.reply_to(message, f"⚠️ Sir, `SUPPORT_BOT_TOKEN` set nahi hai.{FOOTER}", parse_mode="Markdown")
        return

    bot.reply_to(message, "🔍 *Pinging Support Bot system...*", parse_mode="Markdown")
    try:
        url = f"https://api.telegram.org/bot{SUPPORT_BOT_TOKEN}/getMe"
        res = requests.get(url, timeout=5).json()

        if res.get("ok"):
            bot_name = res["result"]["first_name"]
            bot_username = res["result"]["username"]
            bot.reply_to(
                message,
                f"🟢 **SUPPORT BOT IS ONLINE!**\n\n• **Name:** {bot_name}\n• **Username:** @{bot_username}{FOOTER}",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(OWNER_ID, f"🚨 **ALERT: SUPPORT BOT IS OFFLINE!**{FOOTER}", parse_mode="Markdown")
            bot.reply_to(message, f"🔴 **SUPPORT BOT IS OFFLINE!** Alert sent to Owner.{FOOTER}", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(OWNER_ID, f"🚨 **ALERT: UNREACHABLE!**\nError: `{e}`{FOOTER}", parse_mode="Markdown")
        bot.reply_to(message, f"🔴 **SUPPORT BOT UNREACHABLE!**\nError: `{e}`{FOOTER}", parse_mode="Markdown")

@bot.message_handler(commands=['owner'])
def owner_cmd(message):
    register_chat(message.chat.id, message.chat.type)
    user_name = message.from_user.first_name or "User"
    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, f"👑 **Boss Access Confirmed.** Welcome back, {user_name}!{FOOTER}", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"Restricted to Boss.{FOOTER}")

@bot.message_handler(commands=['v', 'voice'])
def handle_voice_chat(message):
    register_chat(message.chat.id, message.chat.type)
    user_name = message.from_user.first_name or "User"
    user_query = message.text.replace('/voice', '').replace('/v', '').strip()
    if not user_query:
        bot.reply_to(message, f"Please query likhein voice mode ke liye.{FOOTER}", parse_mode="Markdown")
        return

    try:
        bot.send_chat_action(message.chat.id, 'record_audio')
        ai_reply = get_groq_response(user_query, user_name=user_name)
        clean_text = ai_reply.replace('*', '').replace('#', '').replace('`', '')
        
        audio_file = "voice_reply.mp3"
        
        async def generate_tts():
            communicate = edge_tts.Communicate(
                clean_text, 
                "hi-IN-MadhurNeural", 
                pitch="-15Hz", 
                rate="-10%"
            )
            await communicate.save(audio_file)

        asyncio.run(generate_tts())

        with open(audio_file, 'rb') as voice:
            bot.send_voice(
                message.chat.id, 
                voice=voice, 
                caption=f"🎙️ **J.A.R.V.I.S. (Deep Voice):**\n\n{ai_reply}{FOOTER}", 
                parse_mode="Markdown"
            )

    except Exception as e:
        bot.reply_to(message, f"Voice Error: `{e}`{FOOTER}", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    register_chat(message.chat.id, message.chat.type)
    user_name = message.from_user.first_name or "User"
    
    clean_prompt = message.text
    if clean_prompt.startswith('/'):
        clean_prompt = clean_prompt.split(' ', 1)[-1]

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_groq_response(clean_prompt, user_name=user_name)
        bot.reply_to(message, f"{ai_reply}{FOOTER}", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Error: `{e}`{FOOTER}", parse_mode="Markdown")

if __name__ == "__main__":
    logging.info("Starting J.A.R.V.I.S. via Long Polling...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logging.warning(f"Webhook cleanup note: {e}")
        
    bot.infinity_polling(timeout=10, long_polling_timeout=5, allowed_updates=['message', 'my_chat_member'])
        
