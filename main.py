import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging Sozlamalari
logging.basicConfig(level=logging.INFO)

# --- BOT SOZLAMALARI ---
TOKEN = os.getenv("BOT_TOKEN", "8827905488:AAF-BsNgLJTIangTAG0-QgF2Z9m6h8lpPQM")

# Kanalingiz havolasi va Instagram profil
CHANNEL_INVITE_LINK = "https://t.me/+6SRxU-O-aYFiZjgy"
INSTAGRAM_URL = "https://www.instagram.com/cz_yagami?igsh=MWt2YzdzNWVrOTc0eA=="


# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Rasmiy Kanalimiz", url=CHANNEL_INVITE_LINK
            )
        ],
        [InlineKeyboardButton("📸 Bizning Instagram", url=INSTAGRAM_URL)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Salom, **{update.effective_user.first_name}**! ⛩️\n\n"
        "🎬 Anime tomosha qilish uchun uning **kodini** (masalan: `1`, `2`...) yuboring!\n\n"
        "Rasmiy tarmoqlarimizga a'zo bo'lishni unutmang 👇",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


# Anime kodini qabul qilish va kanaldan videoni nusxalash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.isdigit():
        msg_id = int(text)
        await update.message.reply_text("⏳ Anime yuklanmoqda, biroz kuting...")

        try:
            # Baza kanalingizdan ("L" kanali) post raqami bo'yicha videoni foydalanuvchiga yuboradi
            # Note: Bot "L" kanalida Admin bo'lishi shart!
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=update.effective_chat.id,  # Forwarding logic
                message_id=msg_id,
            )
        except Exception:
            # Agarda to'g'ridan-to'g'ri forward qilishda xatolik bo'lsa
            await update.message.reply_text(
                "❌ Bunday kodli anime topilmadi yoki hali yuklanmagan!"
            )
    else:
        await update.message.reply_text(
            "❌ Iltimos, faqat anime kodini raqam ko'rinishida yuboring (masalan: 1)!"
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot muvaffaqiyatli ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
    
  
