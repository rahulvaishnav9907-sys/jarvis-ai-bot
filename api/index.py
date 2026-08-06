import os
import logging
import requests
import urllib.parse
from flask import Flask, request
import telebot

logging.basicConfig(level=logging.INFO)

# ----------------- CONFIGURATION -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

# Default to your Owner ID
try:
    OWNER_ID = int(os.environ.get("OWNER_ID", "8088024998"))
except ValueError:
    OWNER_ID = 8088024998

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# Simple memory storage for unique users (Vercel memory lifecycle)
users_list = set()

# Helper function to get Groq AI Response
def get_groq_response(prompt_text):
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
                    "You are J.A.R.V.I.S., a polite, highly intelligent, and witty AI assistant created for Tony Stark. "
                    "Respond concisely in character using terms like 'Sir', 'At your service'. "
                    "Provide clear, crisp, and smart answers in natural Hinglish or English."
                )
            },
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    return "Sir, I encountered an issue accessing my core intelligence processors."

# ----------------- FLASK WEBHOOK ENDPOINT -----------------
@app.route('/', methods=['GET'])
def home():
    return "⚡ J.A.R.V.I.S. Vercel Webhook Active", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

# ----------------- TELEGRAM COMMAND HANDLERS -----------------

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    users_list.add(message.chat.id)
    welcome_text = (
        "🤖 **J.A.R.V.I.S. ONLINE (Groq & Voice Powered)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Good day, Sir! All systems operational at maximum performance.\n\n"
        "⚙️ **Available Controls:**\n"
        "• Just type any message to chat with me.\n"
        "• `/v <message>` or `/voice <message>` : Get a **Voice Response** in deep crystal-clear voice.\n\n"
        "👑 **Owner Commands:**\n"
        "• `/owner` : Check Admin Access & Controls.\n"
        "• `/stats` : System status & active users.\n"
        "• `/broadcast <text>` : Send announcement to users."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['owner'])
def owner_cmd(message):
    if message.from_user.id == OWNER_ID:
        bot.reply_to(
            message,
            f"👑 **Welcome Back, Boss!**\n\n"
            f"• **Owner ID:** `{OWNER_ID}`\n"
            f"• **Access Status:** Full Admin / Root Access Granted.\n"
            f"• **Server:** Vercel Serverless (Ultra Low Latency)\n"
            f"• **AI Engine:** Llama 3.3 Versatile",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message, "⚠️ Access Denied. This command is restricted to the Owner.")

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    if message.from_user.id == OWNER_ID:
        active_count = len(users_list) if users_list else 1
        bot.reply_to(
            message,
            f"📊 **J.A.R.V.I.S. SYSTEM DIAGNOSTICS**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 **Status:** Active & Ready\n"
            f"👥 **Tracked Chats:** {active_count}\n"
            f"⚡ **Voice Engine:** Crisp Deep Speech API\n"
            f"⚡ **LLM Core:** Groq Llama 3.3-70B",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message, "Sir, diagnostic metrics are restricted to Sir Tony Stark.")

@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(message):
    if message.from_user.id == OWNER_ID:
        msg_text = message.text.replace('/broadcast', '').strip()
        if not msg_text:
            bot.reply_to(message, "Sir, please specify the message to broadcast. Example: `/broadcast Hello All`", parse_mode="Markdown")
            return
        
        success = 0
        for uid in list(users_list):
            try:
                bot.send_message(uid, f"📢 **ANNOUNCEMENT FROM SIR:**\n\n{msg_text}", parse_mode="Markdown")
                success += 1
            except Exception:
                pass
        bot.reply_to(message, f"✅ Broadcast sent to {success} users, Sir.", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Sir, broadcasting rights are exclusive to the Boss.")

# ----------------- VOICE RESPONSE COMMAND -----------------
@bot.message_handler(commands=['v', 'voice'])
def handle_voice_chat(message):
    users_list.add(message.chat.id)
    user_query = message.text.replace('/voice', '').replace('/v', '').strip()
    
    if not user_query:
        bot.reply_to(message, "Sir, please type a prompt after the command. Example: `/voice Who created you?`", parse_mode="Markdown")
        return

    try:
        bot.send_chat_action(message.chat.id, 'record_audio')
        ai_reply = get_groq_response(user_query)
        
        # Clean markdown symbols for smooth voice generation
        clean_text = ai_reply.replace('*', '').replace('#', '').replace('`', '')
        
        # Deep Crystal Clear Speech REST API
        encoded_text = urllib.parse.quote(clean_text)
        voice_url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded_text}&tl=en-uk&client=tw-ob"
        
        bot.send_voice(
            message.chat.id,
            voice=voice_url,
            caption=f"🎙️ **J.A.R.V.I.S. Voice Note:**\n\n{ai_reply}",
            parse_mode="Markdown",
            reply_to_message_id=message.message_id
        )
    except Exception as e:
        bot.reply_to(message, f"Sir, error generating audio response: `{e}`", parse_mode="Markdown")

# ----------------- NORMAL CHAT HANDLER -----------------
@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    users_list.add(message.chat.id)
    if not GROQ_API_KEY:
        bot.reply_to(message, "Sir, `GROQ_API_KEY` is not set in Vercel Environment Variables.")
        return

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_groq_response(message.text)
        bot.reply_to(message, ai_reply, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Sir, error encountered: `{e}`", parse_mode="Markdown")
    
