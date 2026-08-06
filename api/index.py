import os
import logging
import requests
import urllib.parse
import telebot

logging.basicConfig(level=logging.INFO)

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8701237136:AAGznwDtx8Gk7KP2I9dd5p09MMyW-ZeVu6A").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
SUPPORT_BOT_TOKEN = os.environ.get("SUPPORT_BOT_TOKEN", "").strip()

try:
    OWNER_ID = int(os.environ.get("OWNER_ID", "8088024998"))
except ValueError:
    OWNER_ID = 8088024998

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Webhook remove kar rahe hain taaki Long Polling activate ho sake
try:
    bot.remove_webhook()
except Exception as e:
    logging.info(f"Webhook remove note: {e}")

def get_groq_response(prompt_text):
    if not GROQ_API_KEY:
        return "Sir, GROQ_API_KEY is missing in environment variables."
    
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
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"Groq API Error: {e}")
    return "Sir, I encountered an issue accessing my core intelligence processors."

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    welcome_text = (
        "🤖 **J.A.R.V.I.S. ONLINE (Render Hosting)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Good day, Sir! All systems operational.\n\n"
        "📊 **Commands:**\n"
        "• `/support_status` : Live check of Support Bot status.\n"
        "• `/v <message>` : Voice mode chat.\n"
        "• `/owner` : Check Root Access."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['support_status'])
def check_support_status(message):
    if not SUPPORT_BOT_TOKEN:
        bot.reply_to(message, "⚠️ Sir, `SUPPORT_BOT_TOKEN` is missing in Environment Variables.", parse_mode="Markdown")
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
                f"🟢 **SUPPORT BOT IS ONLINE!**\n\n• **Name:** {bot_name}\n• **Username:** @{bot_username}",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(OWNER_ID, "🚨 **ALERT: SUPPORT BOT IS OFFLINE!**", parse_mode="Markdown")
            bot.reply_to(message, "🔴 **SUPPORT BOT IS OFFLINE!** Alert sent to Owner.", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(OWNER_ID, f"🚨 **ALERT: UNREACHABLE!**\nError: `{e}`", parse_mode="Markdown")
        bot.reply_to(message, f"🔴 **SUPPORT BOT UNREACHABLE!**\nError: `{e}`", parse_mode="Markdown")

@bot.message_handler(commands=['owner'])
def owner_cmd(message):
    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, "👑 **Boss Access Confirmed.** System Monitoring: **Active**", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Restricted to Boss.")

@bot.message_handler(commands=['v', 'voice'])
def handle_voice_chat(message):
    user_query = message.text.replace('/voice', '').replace('/v', '').strip()
    if not user_query:
        bot.reply_to(message, "Please provide a query for voice mode.", parse_mode="Markdown")
        return

    try:
        bot.send_chat_action(message.chat.id, 'record_audio')
        ai_reply = get_groq_response(user_query)
        clean_text = ai_reply.replace('*', '').replace('#', '').replace('`', '')
        encoded_text = urllib.parse.quote(clean_text)
        voice_url = f"https://dict.youdao.com/dictvoice?audio={encoded_text}&type=2"
        
        bot.send_voice(message.chat.id, voice=voice_url, caption=f"🎙️ **J.A.R.V.I.S.:**\n\n{ai_reply}", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Voice Error: `{e}`", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_groq_response(message.text)
        bot.reply_to(message, ai_reply, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Error: `{e}`", parse_mode="Markdown")

if __name__ == "__main__":
    logging.info("Starting J.A.R.V.I.S. Bot via Infinity Polling...")
    bot.infinity_polling(skip_pending=True)
    
