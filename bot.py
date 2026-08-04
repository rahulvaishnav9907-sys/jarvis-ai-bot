# ----------------- AI CHAT HANDLER (FIXED MODEL CALL) -----------------
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
            
            # Updated correct model string format for google-genai
            response = ai_client.models.generate_content(
                model='models/gemini-1.5-flash',
                contents=prompt,
            )
            
            if response and response.text:
                jarvis.reply_to(message, response.text, parse_mode="Markdown")
            else:
                jarvis.reply_to(message, "Sir, my neural network is cooling down. Please retry shortly.", parse_mode="Markdown")
                
        except Exception as e:
            logging.error(f"AI Error: {e}")
            # Show exact error to trace easily if anything else is missing
            jarvis.reply_to(message, f"Sir, neural error: `{e}`", parse_mode="Markdown")
    else:
        jarvis.reply_to(message, "Sir, `GEMINI_API_KEY` is not set in Environment Variables.")
        
