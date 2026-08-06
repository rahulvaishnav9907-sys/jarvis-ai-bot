import asyncio
import edge_tts

@bot.message_handler(commands=['v', 'voice'])
def handle_voice_chat(message):
    user_query = message.text.replace('/voice', '').replace('/v', '').strip()
    if not user_query:
        bot.reply_to(message, "Please query likhein voice mode ke liye.", parse_mode="Markdown")
        return

    try:
        bot.send_chat_action(message.chat.id, 'record_audio')
        
        # Groq AI se reply lena
        ai_reply = get_groq_response(user_query)
        clean_text = ai_reply.replace('*', '').replace('#', '').replace('`', '')
        
        # Audio file path
        audio_file = "voice_reply.mp3"
        
        # Async function to generate Deep Male Hindi Voice (Microsoft Edge TTS)
        async def generate_tts():
            # 'hi-IN-MadhurNeural' ek deep male Hindi voice hai
            # pitch='-15Hz' aur rate='-10%' se voice Thanos jaisi heavy ho jaati hai
            communicate = edge_tts.Communicate(
                clean_text, 
                "hi-IN-MadhurNeural", 
                pitch="-15Hz", 
                rate="-10%"
            )
            await communicate.save(audio_file)

        # Run TTS async in synchronous telebot handler
        asyncio.run(generate_tts())

        # Send Voice Note to Telegram
        with open(audio_file, 'rb') as voice:
            bot.send_voice(
                message.chat.id, 
                voice=voice, 
                caption=f"🎙️ **J.A.R.V.I.S. (Deep Voice):**\n\n{ai_reply}", 
                parse_mode="Markdown"
            )

    except Exception as e:
        bot.reply_to(message, f"Voice Error: `{e}`", parse_mode="Markdown")
            
