import os
import logging
import asyncio
import datetime
import random
import pytz
import requests
import telebot
import edge_tts
import sqlite3
import html
from threading import Thread
from flask import Flask

logging.basicConfig(level=logging.INFO)

# --- FLASK SERVER FOR RENDER PORT BINDING (24/7 ANTI-SLEEP) ---
app = Flask('')

@app.route('/')
def home():
    return "J.A.R.V.I.S. AI Engine Active & Operational!"

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

# --- DATABASE & CONTEXT MEMORY SETUP ---
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
    return now.strftime("%I:%M %p"), now.strftime("%A, %B %d, %Y")

# --- DYNAMIC 1000+ UNLIMITED ANIME QUIZ FETCH ENGINE ---
def fetch_dynamic_anime_quiz():
    # Category 31 = Anime & Manga in OpenTDB
    url = "https://opentdb.com/api.php?amount=1&category=31&type=multiple"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get('response_code') == 0 and res.get('results'):
            item = res['results'][0]
            question = html.unescape(item['question'])
            correct_ans = html.unescape(item['correct_answer'])
            incorrect_ans = [html.unescape(a) for a in item['incorrect_answers']]
            
            options = incorrect_ans + [correct_ans]
            random.shuffle(options)
            correct_id = options.index(correct_ans)
            
            return {
                "question": question,
                "options": options,
                "correct_id": correct_id,
                "explanation": f"Correct Answer: {correct_ans}"
            }
    except Exception as e:
        logging.error(f"Quiz Fetch Error: {e}")
        
    # Backup static question if API lags
    return {
        "question": "Demon Slayer mein Tanjiro ki behen ka naam kya hai?",
        "options": ["Nezuko", "Kanao", "Mitsuri", "Shinobu"],
        "correct_id": 0,
        "explanation": "Correct Answer: Nezuko Kamado"
    }

# --- HIGH-LEVEL INTELLIGENCE ENGINE ---
def get_groq_response(chat_id, prompt_text, user_name="Boss"):
    if not GROQ_API_KEY:
        return "GROQ_API_KEY environment variable missing hai."
    
    current_time, current_date = get_current_ist_datetime()
    history = get_chat_history(chat_id)

    system_instruction = {
        "role": "system",
        "content": (
            f"You are J.A.R.V.I.S., an advanced AI assistant created and owned by 'Anime Nation'. "
            f"You are talking to '{user_name}'.\n"
            f"STRICT RULES:\n"
            f"1. Your Owner/Creator is strictly 'Anime Nation'. Never mention Tony Stark or Iron Man under any circumstances.\n"
            f"2. Be direct, clear, highly intelligent, and natural. Match response length strictly to user intent.\n"
            f"3. For simple queries or greetings, reply in 1-2 concise, helpful sentences.\n"
            f"4. For technical, coding, or analytical queries, provide comprehensive, well-structured answers using Markdown.\n"
            f"5. Real-time context: Time = {current_time} IST, Date = {current_date}.\n"
            f"6. IMPORTANT: Never mention time or date unless explicitly asked.\n"
            f"7. Do not generate unclosed Markdown syntax."
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

# --- AUTOMATIC REGISTRATION HANDLERS ---
@bot.channel_post_handler(func=lambda message: True)
def track_channel_posts(message):
    register_chat(message.chat.id, "channel")

@bot.my_chat_member_handler()
def track_my_status(message):
    register_chat(message.chat.id, message.chat.type)

# --- START / HELP COMMAND HANDLER ---
@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    register_chat(message.chat.id, message.chat.type)
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"

    if user_id == OWNER_ID:
        total_chats, users_count, groups_count, channels_count = get_chat_metrics()
        quiz_played = get_quiz_total_played()

        support_status_text = "🔴 Offline / Unknown"
        if SUPPORT_BOT_TOKEN:
            try:
                url = f"https://api.telegram.org/bot{SUPPORT_BOT_TOKEN}/getMe"
                res = requests.get(url, timeout=5).json()
                if res.get("ok"):
                    support_status_text = f"🟢 Active (@{res['result']['username']})"
            except Exception:
                support_status_text = "🔴 Unreachable"

        owner_dashboard = (
            f"👑 **OWNER CONTROL PANEL**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Welcome back, Boss ({user_name})!\n\n"
            f"📊 **SYSTEM STATUS & METRICS:**\n"
            f"• **Support Bot Status:** {support_status_text}\n"
            f"• **Total Bot Users:** `{users_count}`\n"
            f"• **Total Channels & Groups Joined:** `{groups_count + channels_count}` (`{groups_count}` Groups | `{channels_count}` Channels)\n"
            f"• **Anime Quiz Game Played:** `{quiz_played}` times\n\n"
            f"🛠️ **ALL BOT COMMANDS:**\n"
            f"• `/start` : Reload Control Dashboard\n"
            f"• `/quiz` : Play Anime Trivia Quiz\n"
            f"• `/v <msg>` : Voice Synthesis Response\n"
            f"• `/broadcast <msg>` : Global Broadcast\n"
            f"• `/stats` : Detailed System Analytics\n"
            f"• `/support_status` : Direct Support Bot Check\n"
            f"• `/owner` : Owner Identity Status"
        )
        bot.reply_to(message, format_text(owner_dashboard), parse_mode="Markdown")
        return

    msg_1 = (
        f"🤖 **Hello {user_name}! Main J.A.R.V.I.S. hoon — aapka personal AI assistant.**\n\n"
        f"Main aapki har cheez me help kar sakta hoon: coding, writing, questions, general knowledge, ya koi bhi problem solve karne me! Sida question puchiye."
    )
    msg_2 = (
        f"🎮 **Is bot me Anime Quiz Game bhi hai!**\n\n"
        f"Aap `/quiz` command type karke anime trivia game khel sakte hain aur apna anime knowledge test kar sakte hain!"
    )
    
    bot.reply_to(message, format_text(msg_1), parse_mode="Markdown")
    bot.send_message(message.chat.id, format_text(msg_2), parse_mode="Markdown")

# --- UNLIMITED DYNAMIC ANIME QUIZ HANDLER ---
@bot.message_handler(commands=['quiz', 'game'])
def anime_quiz_cmd(message):
    register_chat(message.chat.id, message.chat.type)
    record_quiz_play(message.chat.id)
    
    quiz_item = fetch_dynamic_anime_quiz()
    
    bot.send_poll(
        chat_id=message.chat.id,
        question=f"⛩️ Anime Quiz: {quiz_item['question']}",
        options=quiz_item['options'],
        type='quiz',
        correct_option_id=quiz_item['correct_id'],
        explanation=quiz_item['explanation'],
        is_anonymous=False
    )

@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, format_text("⚠️ Access Denied: Authorized for Owner (Anime Nation) only."), parse_mode="Markdown")
        return

    broadcast_msg = message.text.replace('/broadcast', '').strip()
    if not broadcast_msg:
        bot.reply_to(message, format_text("⚠️ Command format: `/broadcast Your Message Here`"), parse_mode="Markdown")
        return

    clean_broadcast_msg = broadcast_msg.replace("⚡ Powered by - Anime Nation", "").replace("⚡ *Powered by - Anime Nation*", "").strip()

    bot.reply_to(message, "📢 *Initiating Global Broadcast across all Groups & Channels...*", parse_mode="Markdown")
    
    all_chats = get_all_chats()
    success = 0
    failed = 0
    error_reasons = []

    for chat_id, chat_type in all_chats:
        if chat_id == OWNER_ID and len(all_chats) > 1:
            continue

        try:
            bot.send_message(
                chat_id, 
                format_text(f"📢 **J.A.R.V.I.S. BROADCAST ANNOUNCEMENT**\n━━━━━━━━━━━━━━━━━━━━━━\n\n{clean_broadcast_msg}"),
                parse_mode="Markdown"
            )
            success += 1
        except Exception:
            try:
                bot.send_message(
                    chat_id, 
                    f"📢 J.A.R.V.I.S. BROADCAST ANNOUNCEMENT\n━━━━━━━━━━━━━━━━━━━━━━\n\n{clean_broadcast_msg}\n\n⚡ Powered by - Anime Nation"
                )
                success += 1
            except Exception as e:
                failed += 1
                error_reasons.append(f"`{chat_id}`: {str(e)[:40]}")

    error_log = "\n".join(error_reasons[:3]) if error_reasons else "None"

    report = (
        f"📊 **BROADCAST REPORT COMPLETE**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 **Successfully Delivered:** `{success}` chats\n"
        f"🔴 **Failed / Removed:** `{failed}` chats\n\n"
        f"⚠️ **Last Errors:**\n{error_log}"
    )
    bot.reply_to(message, format_text(report), parse_mode="Markdown")

@bot.message_handler(commands=['stats', 'users'])
def stats_cmd(message):
    register_chat(message.chat.id, message.chat.type)
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, format_text("⚠️ Access Denied: Authorized for Owner (Anime Nation) only."), parse_mode="Markdown")
        return

    total_chats, users_count, groups_count, channels_count = get_chat_metrics()
    quiz_played = get_quiz_total_played()
    
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
        f"🤖 **J.A.R.V.I.S. AI ENGINE**\n"
        f"• **Owner:** Anime Nation\n"
        f"• **Total Registered Users:** `{users_count}`\n"
        f"• **Total Channels & Groups Joined:** `{groups_count + channels_count}` (`{groups_count}` Groups | `{channels_count}` Channels)\n"
        f"• **Anime Quiz Played Total:** `{quiz_played}` times\n"
        f"• **Status:** 🟢 Active & Operational\n\n"
        f"🎧 **SUPPORT BOT ({support_username})**\n"
        f"• **Status:** {support_status_text}\n\n"
        f"🕒 **SYSTEM TIME (IST):** `{current_time}`\n"
        f"📅 **SYSTEM DATE:** `{current_date}`"
    )
    bot.reply_to(message, format_text(stats_msg), parse_mode="Markdown")

@bot.message_handler(commands=['support_status'])
def check_support_status(message):
    register_chat(message.chat.id, message.chat.type)
    if not SUPPORT_BOT_TOKEN:
        bot.reply_to(message, format_text("⚠️ `SUPPORT_BOT_TOKEN` configured nahi hai."), parse_mode="Markdown")
        return

    try:
        url = f"https://api.telegram.org/bot{SUPPORT_BOT_TOKEN}/getMe"
        res = requests.get(url, timeout=5).json()

        if res.get("ok"):
            bot_name = res["result"]["first_name"]
            bot_username = res["result"]["username"]
            bot.reply_to(
                message,
                format_text(f"🟢 **SUPPORT BOT IS ONLINE!**\n\n• **Name:** {bot_name}\n• **Username:** @{bot_username}"),
                parse_mode="Markdown"
            )
        else:
            bot.send_message(OWNER_ID, format_text("🚨 **ALERT: SUPPORT BOT IS OFFLINE!**"), parse_mode="Markdown")
            bot.reply_to(message, format_text("🔴 **SUPPORT BOT IS OFFLINE!** Alert sent to Owner."), parse_mode="Markdown")
    except Exception as e:
        bot.send_message(OWNER_ID, format_text(f"🚨 **ALERT: UNREACHABLE!**\nError: `{e}`"), parse_mode="Markdown")
        bot.reply_to(message, format_text(f"🔴 **SUPPORT BOT UNREACHABLE!**\nError: `{e}`"), parse_mode="Markdown")

@bot.message_handler(commands=['owner'])
def owner_cmd(message):
    register_chat(message.chat.id, message.chat.type)
    bot.reply_to(message, format_text("👑 **Owner & Developer:** Anime Nation"), parse_mode="Markdown")

@bot.message_handler(commands=['v', 'voice'])
def handle_voice_chat(message):
    register_chat(message.chat.id, message.chat.type)
    user_name = message.from_user.first_name or "User"
    user_query = message.text.replace('/voice', '').replace('/v', '').strip()
    if not user_query:
        bot.reply_to(message, format_text("Query likhein voice response ke liye."), parse_mode="Markdown")
        return

    try:
        bot.send_chat_action(message.chat.id, 'record_audio')
        ai_reply = get_groq_response(message.chat.id, user_query, user_name=user_name)
        clean_text = ai_reply.replace('*', '').replace('#', '').replace('`', '')
        
        audio_file = "voice_reply.mp3"
        
        async def generate_tts():
            communicate = edge_tts.Communicate(
                clean_text[:1000], 
                "hi-IN-MadhurNeural", 
                pitch="-15Hz", 
                rate="-10%"
            )
            await communicate.save(audio_file)

        asyncio.run(generate_tts())

        with open(audio_file, 'rb') as voice:
            try:
                bot.send_voice(
                    message.chat.id, 
                    voice=voice, 
                    caption=format_text(f"🎙️ **J.A.R.V.I.S. (Voice):**\n\n{ai_reply[:900]}..."), 
                    parse_mode="Markdown"
                )
            except Exception:
                bot.send_voice(
                    message.chat.id, 
                    voice=voice, 
                    caption=f"🎙️ J.A.R.V.I.S. (Voice):\n\n{clean_text[:900]}...\n\n⚡ Powered by - Anime Nation"
                )

    except Exception as e:
        bot.reply_to(message, format_text(f"Voice Synthesis Error: `{e}`"), parse_mode="Markdown")

# --- MAIN AI CHAT HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    register_chat(message.chat.id, message.chat.type)
    user_name = message.from_user.first_name or "User"
    
    clean_prompt = message.text
    if clean_prompt.startswith('/'):
        clean_prompt = clean_prompt.split(' ', 1)[-1]

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_groq_response(message.chat.id, clean_prompt, user_name=user_name)
        
        try:
            bot.reply_to(message, format_text(ai_reply), parse_mode="Markdown")
        except Exception:
            plain_footer = "⚡ Powered by - Anime Nation"
            bot.reply_to(message, f"{ai_reply}\n\n{plain_footer}")

    except Exception as e:
        bot.reply_to(message, format_text(f"System Error: `{e}`"), parse_mode="Markdown")

# --- ENTRYPOINT ---
if __name__ == "__main__":
    keep_alive()
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logging.warning(f"Webhook cleanup note: {e}")
        
    bot.infinity_polling(timeout=10, long_polling_timeout=5, allowed_updates=['message', 'my_chat_member', 'channel_post'])
