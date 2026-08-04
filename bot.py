# ----------------- AI CHAT HANDLER -----------------
@jarvis.message_handler(func=lambda message: True)
def handle_ai_chat(message):
    user_text = message.text.lower()
    
    if "status" in user_text or "sysinfo" in user_text:
        if is_boss(message):
            sysinfo_cmd(message)
            return

    if ai_client:
        try:
            jarvis.send_chat_action(message.chat.id, 'typing')
            
            system_prompt = (
                "You are J.A.R.V.I.S., a polite, smart, and witty AI assistant created for Tony Stark (the user). "
                "Respond concisely in character ('Sir', 'At your service'). "
                "Help with technical questions, code, support queries, and general chat in natural Hinglish or English.\n\n"
                f"User: {message.text}"
            )
            
            # Direct model string without 'models/' prefix
            response = ai_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=system_prompt,
            )
            
            if response and response.text:
                jarvis.reply_to(message, response.text, parse_mode="Markdown")
            else:
                jarvis.reply_to(message, "Sir, my neural network is cooling down. Please retry shortly.", parse_mode="Markdown")
                
        except Exception as e:
            logging.error(f"AI Error: {e}")
            jarvis.reply_to(message, f"Sir, neural network error: `{e}`", parse_mode="Markdown")
    else:
        jarvis.reply_to(message, "Sir, `GEMINI_API_KEY` is not set in Environment Variables.")
        
