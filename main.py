import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging
logging.basicConfig(level=logging.INFO)

# --- BOT SOZLAMALARI ---
TOKEN = os.getenv("BOT_TOKEN", "8827905488:AAF-BsNgLJTIangTAG0-QgF2Z9m6h8lpPQM")

# Baza kanal ID-si
CHANNEL_ID = -1003947988121

# Havolalar
CHANNEL_INVITE_LINK = "https://t.me/+6SRxU-O-aYFiZjgy"
INSTAGRAM_URL = "https://www.instagram.com/cz_yagami?igsh=MWt2YzdzNWVrOTc0eA=="

# Admin Telegram ID (Light / @LeviAckerman765)
ADMIN_ID = 5560186689

# Foydalanuvchilar ro'yxati
USERS = set()


# Kanallarga obunani tekshirish
async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID, user_id=user_id
        )
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logging.error(f"Obuna tekshirishda xatolik: {e}")
        return True


# Obuna tugmalari
def get_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Rasmiy Kanalimiz", url=CHANNEL_INVITE_LINK)],
        [InlineKeyboardButton("📸 Bizning Instagram", url=INSTAGRAM_URL)],
        [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")],
    ]
    return InlineKeyboardMarkup(keyboard)


# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS.add(user_id)

    if not await is_subscribed(user_id, context):
        await update.message.reply_text(
            "⚠️ **Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'ling!**\n\n"
            "A'zo bo'lgach, **'✅ Obunani tekshirish'** tugmasini bosing.",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"Salom, **{update.effective_user.first_name}**! ⛩️\n\n"
        "🎬 Anime tomosha qilish uchun uning **kodini** (masalan: `1`, `2`...) yuboring!\n\n"
        "Yoqimli tomosha! 🍿",
        parse_mode="Markdown",
    )


# Obunani tekshirish tugmasi bosilganda
async def check_sub_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if await is_subscribed(user_id, context):
        await query.message.edit_text(
            "✅ **Obunangiz tasdiqlandi!**\n\n"
            "Endi anime kodini (masalan: `1` yoki `2`) yuborishingiz mumkin! ⛩️",
            parse_mode="Markdown",
        )
    else:
        await query.message.reply_text(
            "❌ Hali kanalimizga a'zo bo'lmadingiz. Iltimos, avval a'zo bo'ling!",
            show_alert=True,
        )


# Anime kodini qabul qilish
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS.add(user_id)

    if not await is_subscribed(user_id, context):
        await update.message.reply_text(
            "⚠️ Botdan foydalanish uchun kanalimizga a'zo bo'lishingiz kerak!",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown",
        )
        return

    text = update.message.text.strip()

    if text.isdigit():
        msg_id = int(text)
        await update.message.reply_text("⏳ Anime yuklanmoqda, biroz kuting...")

        try:
            # Kanaldagi post raqami bo'yicha videoni foydalanuvchiga yuboradi
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=msg_id,
            )
        except Exception:
            await update.message.reply_text(
                "❌ Bunday kodli anime topilmadi yoki hali yuklanmagan!"
            )
    else:
        await update.message.reply_text(
            "❌ Iltimos, faqat anime kodini raqam ko'rinishida yuboring (masalan: 1)!"
        )


# Admin uchun /stat buyrug'i
async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            f"📊 **BOT STATISTIKASI:**\n\n" f"👥 Jami foydalanuvchilar: **{len(USERS)}** ta",
            parse_mode="Markdown",
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stat", stat))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Bot muvaffaqiyatli ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
    
    
  
