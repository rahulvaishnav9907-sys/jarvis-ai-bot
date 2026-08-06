# 📊 TOTAL USERS & SYSTEM STATS COMMAND (Boss Only)
@bot.message_handler(commands=['stats', 'users'])
def stats_cmd(message):
    register_chat(message.chat.id)
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, f"⚠️ Access Denied: Sirf Boss hi stats check kar sakte hain.{FOOTER}", parse_mode="Markdown")
        return

    bot.reply_to(message, "🔄 *Fetching J.A.R.V.I.S. & Support Bot metrics...*", parse_mode="Markdown")

    # J.A.R.V.I.S. Metrics
    jarvis_chats_count = len(active_chats)
    
    # Support Bot Status Check
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

    stats_msg = (
        f"📊 **SYSTEM METRICS REPORT**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 **J.A.R.V.I.S. AI BOT**\n"
        f"• **Total Active Users & Chats:** `{jarvis_chats_count}`\n"
        f"• **Status:** 🟢 Online & Running\n\n"
        f"🎧 **SUPPORT BOT ({support_username})**\n"
        f"• **Status:** {support_status_text}\n"
        f"• **Tracking Mode:** Integrated\n"
        f"{FOOTER}"
    )
    
    bot.reply_to(message, stats_msg, parse_mode="Markdown")
    
