import os
import logging
import urllib.parse
from flask import Flask, request
import requests
import telebot

logging.basicConfig(level=logging.INFO)

# ----------------- CONFIGURATION -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
SUPPORT_BOT_TOKEN = os.environ.get("SUPPORT_BOT_TOKEN", "").strip()

try:
    OWNER_ID = int(os.environ.get("OWNER_ID", "8088024998"))
except ValueError:
    OWNER_ID = 8088024998

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# Helper function for Groq AI
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
                "content": "You are J.A.R.V.I.S., a polite, smart, and witty AI assistant created for Tony Stark. Respond concisely in character."
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
    return "⚡ J.A.R.V.I.S. Core & Support Monitor Active", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

# ----------------- TELEGRAM COMMANDS -----------------

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    welcome_text = (
        "🤖 **J.A.R.V.I.S. ONLINE (Support Bot Monitor)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Good day, Sir! All systems operational.\n\n"
        "📊 **Support Monitoring Commands:**\n"
        "• `/support_status` : Live status check of your Support Bot.\n"
        "• `/v <message>` : Deep voice mode chat.\n\n"
        "👑 **Owner Commands:**\n"
        "• `/owner` : Check Root Access."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['support_status'])
def check_support_status(message):
    if not SUPPORT_BOT_TOKEN:
        bot.reply_to(message, "⚠️ Sir, `SUPPORT_BOT_TOKEN` is not set in Vercel Environment Variables.", parse_mode="Markdown")
        return

    bot.reply_to(message, "🔍 *Pinging Support Bot system...*", parse_mode="Markdown")
    
    try:
        url = f"https://api.telegram.org/bot{SUPPORT_BOT_TOKEN}/getMe"
        res = requests.get(url, timeout=5).json()

        if res.get("ok"):
            bot_name = res["result"]["first_name"]
            bot_username = res["result"]["username"]
            
            report = (
                f"🟢 **SUPPORT BOT IS ACTIVE & ONLINE!**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• **Bot Name:** {bot_name}\n"
                f"• **Username:** @{bot_username}\n"
                f"• **Host Status:** Active & Responding\n"
                f"• **Telegram API:** Connected"
            )
            bot.reply_to(message, report, parse_mode="Markdown")
        else:
            # Alert to Owner
            alert_text = (
                "🚨 **J.A.R.V.I.S. SYSTEM ALERT**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ **SUPPORT BOT IS OFFLINE!**\n\n"
                "Sir, your Support Bot server on Render appears to be DOWN or token revoked."
            )
            bot.send_message(OWNER_ID, alert_text, parse_mode="Markdown")
            bot.reply_to(message, "🔴 **SUPPORT BOT IS OFFLINE!** Alert sent to Owner.", parse_mode="Markdown")

    except Exception as e:
        bot.send_message(OWNER_ID, f"🚨 **ALERT: SUPPORT BOT UNREACHABLE!**\nError: `{e}`", parse_mode="Markdown")
        bot.reply_to(message, f"🔴 **SUPPORT BOT IS OFFLINE!**\nError: `{e}`", parse_mode="Markdown")

@bot.message_handler(commands=['owner'])
def owner_cmd(message):
    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, "👑 **Boss Access Confirmed.** System Monitoring: **Active**", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Restricted to Boss.")

# ----------------- VOICE RESPONSE COMMAND -----------------
@bot.message_handler(commands=['v', 'voice'])
def handle_voice_chat(message):
    user_query = message.text.replace('/voice', '').replace('/v', '').strip()
    if not user_query:
        bot.reply_to(message, "Type prompt. Example: `/v Who are you?`", parse_mode="Markdown")
        return

    try:
        bot.send_chat_action(message.chat.id, 'record_audio')
        ai_reply = get_groq_response(user_query)
        clean_text = ai_reply.replace('*', '').replace('#', '').replace('`', '')
        encoded_text = urllib.parse.quote(clean_text)
        voice_url = f"https://dict.youdao.com/dictvoice?audio={encoded_text}&type=2"
        
        bot.send_voice(message.chat.id, voice=voice_url, caption=f"🎙️ **J.A.R.V.I.S.:**\n\n{ai_reply}", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Voice error: `{e}`", parse_mode="Markdown")

# ----------------- GENERAL CHAT -----------------
@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_groq_response(message.text)
        bot.reply_to(message, ai_reply, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Error: `{e}`", parse_mode="Markdown")
    
