import asyncio
import logging
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import aiosqlite
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Logging
logging.basicConfig(level=logging.INFO)

# --- BOT VA KANAL SOZLAMALARI ---
TOKEN = os.getenv("BOT_TOKEN", "8827905488:AAF-BsNgLJTIangTAG0-QgF2Z9m6h8lpPQM")
CHANNEL_ID = -1003947988121
CHANNEL_INVITE_LINK = "https://t.me/+6SRxU-O-aYFiZjgy"
INSTAGRAM_URL = "https://www.instagram.com/cz_yagami?igsh=MWt2YzdzNWVrOTc0eA=="
ADMIN_ID = 5560186689
DB_NAME = "anime.db"

SPAM_THRESHOLD = 1.2
LAST_MESSAGE_TIME = {}
BROADCAST_STATE = 1

# --- RENDER PORT HEALTH CHECK ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
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

# --- DATABASE ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS animes (
                code INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT DEFAULT 'Umumiy',
                message_id INTEGER NOT NULL
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER,
                code INTEGER,
                PRIMARY KEY (user_id, code)
            )
        ''')
        await db.commit()

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            return [row[0] for row in await cursor.fetchall()]

async def get_users_count() -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            res = await cursor.fetchone()
            return res[0] if res else 0

async def add_anime(code: int, title: str, category: str, message_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR REPLACE INTO animes (code, title, category, message_id) VALUES (?, ?, ?, ?)',
            (code, title, category, message_id)
        )
        await db.commit()

async def get_anime_by_code(code: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT title, category, message_id FROM animes WHERE code = ?', (code,)) as cursor:
            return await cursor.fetchone()

async def search_anime(query: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT code, title FROM animes WHERE LOWER(title) LIKE ? LIMIT 10', (f"%{query.lower()}%",)) as cursor:
            return await cursor.fetchall()

async def get_categories():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT DISTINCT category FROM animes') as cursor:
            return [row[0] for row in await cursor.fetchall()]

async def get_animes_by_category(category: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT code, title FROM animes WHERE category = ? LIMIT 20', (category,)) as cursor:
            return await cursor.fetchall()

async def toggle_favorite(user_id: int, code: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT 1 FROM favorites WHERE user_id = ? AND code = ?', (user_id, code)) as cursor:
            exists = await cursor.fetchone()
        if exists:
            await db.execute('DELETE FROM favorites WHERE user_id = ? AND code = ?', (user_id, code))
            await db.commit()
            return False
        else:
            await db.execute('INSERT INTO favorites (user_id, code) VALUES (?, ?)', (user_id, code))
            await db.commit()
            return True

async def get_user_favorites(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('''
            SELECT a.code, a.title FROM favorites f 
            JOIN animes a ON f.code = a.code 
            WHERE f.user_id = ?
        ''', (user_id,)) as cursor:
            return await cursor.fetchall()

# --- KEYBOARDS ---
def get_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Rasmiy Kanalimiz", url=CHANNEL_INVITE_LINK)],
        [InlineKeyboardButton("📸 Bizning Instagram", url=INSTAGRAM_URL)],
        [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_reply_keyboard():
    keyboard = [
        ["🔍 Qidiruv", "📂 Kategoriyalar"],
        ["❤️ Sevimlilar", "ℹ️ Bot haqida"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_anime_action_keyboard(code: int):
    keyboard = [
        [InlineKeyboardButton("❤️ / 💔 Sevimlilarga qo'shish/o'chirish", callback_data=f"fav_{code}")],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- CHECK SUBSCRIPTION ---
async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logging.error(f"Obuna tekshirishda xatolik: {e}")
        return True

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await add_user(user_id)

    if not await is_subscribed(user_id, context):
        await update.message.reply_text(
            "⚠️ **Botdan foydalanish uchun rasmiy kanalimiz va Instagram sahifamizga a'zo bo'ling!**\n\n"
            "A'zo bo'lgach, **'✅ Obunani tekshirish'** tugmasini bosing.",
            reply_markup=get_sub_keyboard(), parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"Salom, **{update.effective_user.first_name}**! ⛩️\n\n"
        "🎬 Anime tomosha qilish uchun uning **kodini** (masalan: `1`, `2`...) yuboring yoki nomini yozib qidiring!",
        reply_markup=get_main_reply_keyboard(), parse_mode="Markdown"
    )

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_subscribed(query.from_user.id, context):
        await query.message.edit_text("✅ **Obunangiz tasdiqlandi!** Endi anime kodini yuborishingiz mumkin. 🍿", parse_mode="Markdown")
    else:
        await query.message.reply_text("❌ Hali kanalimizga a'zo bo'lmadingiz. Iltimos, avval a'zo bo'ling!", show_alert=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = time.time()

    if user_id in LAST_MESSAGE_TIME and (now - LAST_MESSAGE_TIME[user_id]) < SPAM_THRESHOLD:
        await update.message.reply_text("⚠️ **Iltimos, ketma-ket juda tez xabar yubormang!**", parse_mode="Markdown")
        return
    LAST_MESSAGE_TIME[user_id] = now

    await add_user(user_id)

    if not await is_subscribed(user_id, context):
        await update.message.reply_text("⚠️ Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'ling!", reply_markup=get_sub_keyboard())
        return

    text = update.message.text.strip()

    if text == "🔍 Qidiruv":
        await update.message.reply_text("🔍 **Anime nomini yozib yuboring (masalan: `Death Note`):**", parse_mode="Markdown")
        return
    elif text == "❤️ Sevimlilar":
        favs = await get_user_favorites(user_id)
        if not favs:
            await update.message.reply_text("💔 **Sevimlilar ro'yxatingiz hozircha bo'sh!**", parse_mode="Markdown")
            return
        msg = "❤️ **Sizning Sevimli Animelaringiz:**\n\n"
        for code, title in favs:
            msg += f"🎬 **{title}** — Kodi: `{code}`\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    elif text == "📂 Kategoriyalar":
        cats = await get_categories()
        if not cats:
            await update.message.reply_text("📂 Hozircha bazada kategoriyalar mavjud emas.")
            return
        msg = "📂 **Mavjud Kategoriyalar:**\n\n" + "\n".join([f"• `{c}`" for c in cats])
        msg += "\n\nKategoriya bo'yicha ko'rish uchun o'sha kategoriya nomini botga yozib yuboring."
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    elif text == "ℹ️ Bot haqida":
        await update.message.reply_text("⛩️ **Anime Bot** — Sizga eng sevimli animelaringizni sifatli va tezkor taqdim etuvchi bot!", parse_mode="Markdown")
        return

    cats = await get_categories()
    if text in cats:
        animes = await get_animes_by_category(text)
        msg = f"📂 **{text}** kategoriyasidagi animelar:\n\n"
        for code, title in animes:
            msg += f"🎬 **{title}** — Kodi: `{code}`\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if text.isdigit():
        code = int(text)
        anime = await get_anime_by_code(code)
        msg_id = anime[2] if anime else code

        await update.message.reply_text("⏳ Anime yuklanmoqda, biroz kuting...")
        try:
            await context.bot.copy_message(
                chat_id=update.effective_chat.id, 
                from_chat_id=CHANNEL_ID, 
                message_id=msg_id,
                reply_markup=get_anime_action_keyboard(code)
            )
        except Exception:
            await update.message.reply_text("❌ Bunday kodli anime topilmadi yoki xabar kanaldan o'chirilgan!")
    else:
        results = await search_anime(text)
        if not results:
            await update.message.reply_text("❌ Afsuski, bunday nomli anime topilmadi.")
            return
        msg = "🔍 **Topilgan Animelar:**\n\n"
        for code, title in results:
            msg += f"🎬 **{title}** — Kodi: `{code}`\n"
        msg += "\n👇 *Ko'rish uchun anime kodini raqam shaklida yuboring!*"
        await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("fav_"):
        code = int(data.split("_")[1])
        status = await toggle_favorite(query.from_user.id, code)
        text = "❤️ Sevimlilarga qo'shildi!" if status else "💔 Sevimlilardan olib tashlandi!"
        await query.message.reply_text(text)

# --- ADMIN PANEL ---
async def stat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    count = await get_users_count()
    await update.message.reply_text(
        f"👑 **ADMIN PANEL**\n\n"
        f"📊 **Bot foydalanuvchilari:** `{count}` ta\n\n"
        f"⚙️ **Buyruqlar:**\n"
        f"👉 `/add kod | nomi | kategoriya | post_id`\n"
        f"👉 `/send` - Broadcast yuborish",
        parse_mode="Markdown"
    )

async def add_anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        raw_text = " ".join(context.args)
        parts = [p.strip() for p in raw_text.split("|")]
        code = int(parts[0])
        title = parts[1]
        category = parts[2]
        msg_id = int(parts[3])

        await add_anime(code, title, category, msg_id)
        await update.message.reply_text(f"✅ **Anime bazaga qo'shildi!**\nKodi: `{code}`\nNomi: **{title}**\nKategoriya: **{category}**", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Noto'g'ri format!\nMasalan: `/add 1 | Death Note | Detektiv | 2`", parse_mode="Markdown")

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    await update.message.reply_text("📢 **Barcha foydalanuvchilarga yuboriladigan xabarni kiriting (yoki /cancel yozing):**")
    return BROADCAST_STATE

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await get_all_users()
    count = 0
    await update.message.reply_text("🚀 Broadcast boshlandi...")

    for u_id in users:
        try:
            await update.message.copy(chat_id=u_id)
            count += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass

    await update.message.reply_text(f"✅ Xabar muvaffaqiyatli **{count}** ta foydalanuvchiga yetkazildi!")
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Broadcast bekor qilindi.")
    return ConversationHandler.END

# --- MAIN RUNNER ---
async def run_bot():
    await init_db()
    app = Application.builder().token(TOKEN).build()

    broadcast_handler = ConversationHandler(
        entry_points=[CommandHandler("send", start_broadcast)],
        states={BROADCAST_STATE: [MessageHandler(filters.ALL & ~filters.COMMAND, send_broadcast)]},
        fallbacks=[CommandHandler("cancel", cancel_broadcast)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stat", stat_command))
    app.add_handler(CommandHandler("add", add_anime_command))
    app.add_handler(broadcast_handler)

    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^fav_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot muvaffaqiyatli ishga tushdi va Polling boshlandi...")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Bot to'xtab qolmasligi uchun kutish
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    # Health check serverini fonda ishga tushiramiz
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    
    # Event loop ni to'g'ri shaklda yuritish
    asyncio.run(run_bot())
    

