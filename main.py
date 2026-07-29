import asyncio
import logging
import os
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging
logging.basicConfig(level=logging.INFO)

# --- SOZLAMALAR ---
TOKEN = os.getenv("BOT_TOKEN", "8827905488:AAF-BsNgLJTIangTAG0-QgF2Z9m6h8lpPQM")
CHANNEL_ID = -1003947988121 
INSTAGRAM_URL = "https://www.instagram.com/cz_yagami?igsh=MWt2YzdzNWVrOTc0eA=="
ADMIN_ID = 5560186689 

DB_NAME = "users.db"

# --- RENDER HEALTH CHECK SERVER ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

    def log_message(self, format, *args):
        pass

def start_health_server():
    try:
        port = int(os.getenv("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
        server.serve_forever()
    except Exception as e:
        logging.error(f"Health server error: {e}")

# --- BAZA (SQLITE) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

def add_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_users_count() -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# --- TUGMALAR ---
def get_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("📸 Instagram sahifamiz", url=INSTAGRAM_URL)],
        [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- HANDLERLAR ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    
    first_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Salom, **{first_name}**! 🎬\n\n"
        "⚠️ Botdan foydalanish uchun avval **Instagram** sahifamizga a'zo bo'ling va **'✅ Obunani tekshirish'** tugmasini bosing!",
        reply_markup=get_sub_keyboard(),
        parse_mode="Markdown"
    )

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.edit_text(
        "✅ **Obuna tasdiqlandi!**\n\n"
        "Endi ko'rmoqchi bo'lgan animengizning **kodini (masalan: 1, 2, 3...)** yuboring! 🍿",
        parse_mode="Markdown"
    )

async def stat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    count = get_users_count()
    await update.message.reply_text(
        f"📊 **BOT STATISTIKASI**\n\n"
        f"👤 Jami foydalanuvchilar soni: `{count}` ta",
        parse_mode="Markdown"
    )

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    text = update.message.text.strip()

    if text.isdigit():
        msg_id = int(text)
        await update.message.reply_text("⏳ Anime qidirilmoqda...")
        try:
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=msg_id
            )
        except Exception as e:
            logging.error(f"Post yuborishda xatolik: {e}")
            await update.message.reply_text(
                "❌ **Bunday kodli anime topilmadi!**\n\n"
                "Iltimos, kod to'g'riligini tekshirib qaytadan kiriting.",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            "⚠️ Iltimos, anime **kodini (raqam)** yuboring!\n\n"
            "Agar hali Instagram sahifamizga a'zo bo'lmagan bo'lsangiz, a'zo bo'ling:",
            reply_markup=get_sub_keyboard()
        )

# --- MAIN ASYNC ---
async def main():
    init_db()

    # Health check serverni fonda yurgizamiz
    threading.Thread(target=start_health_server, daemon=True).start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stat", stat_command))
    application.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))

    async with application:
        await application.start()
        await application.updater.start_polling()
        print("🚀 Bot muvaffaqiyatli ishga tushdi va ishlamoqda!")
        # Bot to'xtab qolmasligi uchun cheksiz loop
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
            
    
