import os
import logging
import requests
from flask import Flask, request
import telebot

logging.basicConfig(level=logging.INFO)

# ----------------- CONFIGURATION -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

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
        "🤖 **J.A.R.V.I.S. ONLINE (Vercel Serverless)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Good day, Sir! Powered by Stable REST API Architecture.\n\n"
        "💡 *How may I assist you today?*"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    if not GEMINI_API_KEY:
        bot.reply_to(message, "Sir, `GEMINI_API_KEY` is not set in Vercel Environment Variables.")
        return

    try:
        bot.send_chat_action(message.chat.id, 'typing')

        prompt = (
            "You are J.A.R.V.I.S., a polite, smart, and witty AI assistant created for Tony Stark (the user). "
            "Respond concisely in character ('Sir', 'At your service'). "
            "Help with technical questions, code, and general chat in natural Hinglish or English.\n\n"
            f"User: {message.text}"
        )

        # Direct REST API endpoint (No SDK dependency, no version errors)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }

        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()

        if response.status_code == 200:
            ai_reply = res_data['candidates'][0]['content']['parts'][0]['text']
            bot.reply_to(message, ai_reply, parse_mode="Markdown")
        else:
            error_msg = res_data.get('error', {}).get('message', 'Unknown API Error')
            bot.reply_to(message, f"Sir, API Error: `{error_msg}`", parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"Sir, error encountered: `{e}`", parse_mode="Markdown")
    
