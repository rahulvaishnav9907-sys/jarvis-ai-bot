import os
import logging
from flask import Flask, request
import telebot
from google import genai

logging.basicConfig(level=logging.INFO)

# ----------------- CONFIGURATION -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

try:
    OWNER_ID = int(os.environ.get("OWNER_ID", "8088024998"))
except ValueError:
    OWNER_ID = 8088024998

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# Configure New Google GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

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
        "Good day, Sir! Powered by Gemini AI on Serverless Architecture.\n\n"
        "💡 *How may I assist you today?*"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    if client:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            
            prompt = (
                "You are J.A.R.V.I.S., a polite, smart, and witty AI assistant created for Tony Stark (the user). "
                "Respond concisely in character ('Sir', 'At your service'). "
                "Help with technical questions, code, and general chat in natural Hinglish or English.\n\n"
                f"User: {message.text}"
            )
            
            # Latest Google GenAI API Call
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            
            if response and response.text:
                bot.reply_to(message, response.text, parse_mode="Markdown")
            else:
                bot.reply_to(message, "Sir, my systems are temporarily busy.", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Sir, error encountered: `{e}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Sir, `GEMINI_API_KEY` is not set.")
