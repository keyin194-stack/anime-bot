import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8827905488:AAF-BsNgLJTIangTAG0-QgF2Z9m6h8lpPQM"

# 1-Anime videosining havolasi
VIDEO_URL = "https://www.w3schools.com/html/mov_bbb.mp4" 

# Instagram havolangiz
INSTAGRAM_URL = "https://www.instagram.com/cz_yagami?igsh=MWt2YzdzNWVrOTc0eA=="

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📸 Bizning Instagram", url=INSTAGRAM_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Salom, {update.effective_user.first_name}! ⛩️\n\n"
        "Anime tomosha qilish uchun **1** kodini yuboring!\n\n"
        "Instagram sahifamizga ham a'zo bo'lishni unutmang 👇",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "1":
        await update.message.reply_text("⏳ Anime yuklanmoqda, biroz kuting...")
        
        keyboard = [
            [InlineKeyboardButton("📸 Instagram Sahifamiz", url=INSTAGRAM_URL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_video(
            video=VIDEO_URL,
            caption="🎬 **1-Anime (1-Qism)** Uzbek tilida!\n\nYoqimli tomosha!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ Hozircha faqat **1** kodi mavjud.\n"
            "Anime ko'rish uchun **1** deb yozib yuboring!"
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
  
