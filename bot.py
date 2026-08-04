import os
import time
import threading
import logging
import psutil
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai

# ----------------- LOGGING & CONFIG -----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

try:
    OWNER_ID = int(os.environ.get("OWNER_ID", "8088024998"))
except ValueError:
    OWNER_ID = 8088024998

# 1. INITIALIZE BOT FIRST (Isse Line 2 NameError nahi aayega)
jarvis = telebot.TeleBot(BOT_TOKEN)
web_app = Flask(__name__)

# 2. INITIALIZE GEMINI CLIENT
ai_client = None
if GEMINI_API_KEY:
    try:
        ai_client = genai.Client(api_key=GEMINI_API_KEY)
        logging.info("Connected successfully to Google GenAI Client!")
    except Exception as e:
        logging.error(f"GenAI Init Error: {e}")

# ----------------- FLASK DUMMY SERVER (Keep Alive) -----------------
@web_app.route('/')
def root():
    return "⚡ J.A.R.V.I.S. Core Online & Operational", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    web_app.run(host='0.0.0.0', port=port)

# ----------------- HELPER FUNCTIONS -----------------
def is_boss(message):
    return message.from_user.id == OWNER_ID

# ----------------- TELEGRAM COMMAND HANDLERS -----------------
@jarvis.message_handler(commands=['start', 'help'])
def start_cmd(message):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💻 System Diagnostics", callback_data="sys_info"),
        InlineKeyboardButton("🎧 Support Status", callback_data="supp_info")
    )
    welcome_text = (
        "🤖 **J.A.R.V.I.S. ALL-IN-ONE SYSTEM ACTIVE**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Good day, Sir! I am J.A.R.V.I.S., your personal AI assistant, support engine, and system monitor.\n\n"
        "💡 *How can I assist you today? Just send me a message!*"
    )
    jarvis.reply_to(message, welcome_text, parse_mode="Markdown", reply_markup=markup)

@jarvis.message_handler(commands=['sysinfo', 'status'])
def sysinfo_cmd(message):
    if not is_boss(message): return
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    info = (
        "💻 **J.A.R.V.I.S. CORE DIAGNOSTICS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ **CPU Load:** `{cpu}%`\n"
        f"🧠 **RAM Usage:** `{ram}%`\n"
        f"🌐 **Server State:** `Operational`\n"
        f"🤖 **AI Engine:** `Online (Gemini)`"
    )
    jarvis.reply_to(message, info, parse_mode="Markdown")

# ----------------- AI CHAT HANDLER -----------------
@jarvis.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    user_text = message.text.lower()
    
    # Fast local commands
    if "status" in user_text or "sysinfo" in user_text:
        if is_boss(message):
            sysinfo_cmd(message)
            return

    # Gemini AI Processing
    if ai_client:
        try:
            jarvis.send_chat_action(message.chat.id, 'typing')
            
            prompt = (
                "You are J.A.R.V.I.S., a polite, smart, and witty AI assistant created for Tony Stark (the user). "
                "Respond concisely in character ('Sir', 'At your service'). "
                "Help with technical questions, code, support queries, and general chat in natural Hinglish or English.\n\n"
                f"User: {message.text}"
            )
            
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            
            if response and response.text:
                jarvis.reply_to(message, response.text, parse_mode="Markdown")
            else:
                jarvis.reply_to(message, "Sir, my neural network is cooling down. Please retry shortly.", parse_mode="Markdown")
                
        except Exception as e:
            logging.error(f"AI Error: {e}")
            jarvis.reply_to(message, f"Sir, neural error: `{e}`", parse_mode="Markdown")
    else:
        jarvis.reply_to(message, "Sir, `GEMINI_API_KEY` is not set in Environment Variables.")

# ----------------- CALLBACK BUTTONS -----------------
@jarvis.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "sys_info":
        if call.from_user.id == OWNER_ID:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            jarvis.answer_callback_query(call.id, f"CPU: {cpu}% | RAM: {ram}%", show_alert=True)
        else:
            jarvis.answer_callback_query(call.id, "Access restricted to Boss.", show_alert=True)
    elif call.data == "supp_info":
        jarvis.answer_callback_query(call.id, "J.A.R.V.I.S. Support Engine is fully online!", show_alert=True)

# ----------------- MAIN RUNNER -----------------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    logging.info("J.A.R.V.I.S. Core Engine Initialized...")
    jarvis.infinity_polling()
