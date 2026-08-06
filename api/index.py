import os
import logging
import requests
from flask import Flask, request
import telebot

logging.basicConfig(level=logging.INFO)

# ----------------- CONFIGURATION -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

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

# ----------------- TELEGRAM HANDLERS -----------------
@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    welcome_text = (
        "🤖 **J.A.R.V.I.S. ONLINE (Groq Powered)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Good day, Sir! Systems are running at maximum capacity.\n\n"
        "💡 *How may I assist you today?*"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    if not GROQ_API_KEY:
        bot.reply_to(message, "Sir, `GROQ_API_KEY` is not set in Vercel Environment Variables.")
        return

    try:
        bot.send_chat_action(message.chat.id, 'typing')

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
                    "content": "You are J.A.R.V.I.S., a polite, smart, and witty AI assistant created for Tony Stark (the user). Respond concisely in character ('Sir', 'At your service'). Help in natural Hinglish or English."
                },
                {
                    "role": "user",
                    "content": message.text
                }
            ],
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        res_data = response.json()

        if response.status_code == 200:
            ai_reply = res_data['choices'][0]['message']['content']
            bot.reply_to(message, ai_reply, parse_mode="Markdown")
        else:
            error_msg = res_data.get('error', {}).get('message', 'Unknown API Error')
            bot.reply_to(message, f"Sir, Groq API Error: `{error_msg}`", parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"Sir, error encountered: `{e}`", parse_mode="Markdown")
    
