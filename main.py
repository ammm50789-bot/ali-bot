import asyncio
import logging
import time
import random
import aiohttp
import aiosqlite
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    Application,
)

# ==========================================
# ⚙️ CONFIGURATION (Hardcoded as requested)
# ==========================================
TELEGRAM_BOT_TOKEN = "8730185611:AAG3H6UE1n9c-FPyA9XB5FRcOW0-ac-uxVc"
ADMIN_ID = 8195946863
ADMIN_PASSWORD = "11223344Ali"

API_URL = 'https://api.bdg88zf.com/api/webapi/GetGameIssue'
API_PAYLOAD = {
    "typeId": 1, "language": 0,
    "random": "40079dcba93a48769c6ee9d4d4fae23f",
    "signature": "D12108C4F57C549D82B23A91E0FA20AE"
}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

is_global_running = False
automation_task = None
user_states = {}

DB_NAME = "bot_database.db"

# ==========================================
# 🌐 DUMMY WEB SERVER (RAILWAY CRASH FIX)
# ==========================================
# Railway kills apps that don't bind to a port. This keeps it alive.
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running on Railway!")
    def log_message(self, format, *args):
        pass # Disable logging for healthchecks

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

def keep_alive():
    t = threading.Thread(target=run_dummy_server)
    t.daemon = True
    t.start()

# ==========================================
# 💾 ASYNC DATABASE
# ==========================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT, size TEXT, nums TEXT, result_size TEXT, win_loss TEXT, status TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, game_uid TEXT, status TEXT DEFAULT 'NEW', joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        await db.execute("CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_uid INTEGER, channel_id TEXT, is_running INTEGER DEFAULT 0)")
        await db.commit()

async def post_init(application: Application):
    """Sync DB init with Telegram Event Loop to prevent crashes"""
    await init_db()

async def get_setting(key):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def set_setting(key, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

async def get_active_channels():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT channel_id FROM channels WHERE is_running = 1") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

# ==========================================
# 🌐 ENGINE & PREDICTION
# ==========================================
async def get_wingo_data():
    try:
        payload = API_PAYLOAD.copy()
        payload["timestamp"] = int(time.time())
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, timeout=5) as response:
                data = await response.json()
                if "data" in data and "issueNumber" in data["data"]:
                    return data["data"]["issueNumber"], datetime.utcnow().second
    except:
        pass
    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    minutes_passed = (ist_now.hour * 60) + ist_now.minute + 1
    period_str = f"{ist_now.strftime('%Y%m%d')}1000{minutes_passed:04d}"
    return period_str, ist_now.second

async def get_next_prediction():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT result_size FROM history WHERE status='DONE' ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
    pred_size = row[0] if (row and row[0]) else "BIG"
    if pred_size == "BIG":
        nums = random.sample([5, 6, 7, 8, 9], 2)
    else:
        nums = random.sample([0, 1, 2, 3, 4], 2)
    return pred_size, f"{nums[0]}, {nums[1]}"

# ==========================================
# 🤖 AUTOMATION WORKER (Broadcaster)
# ==========================================
async def broadcast_to_channels(bot, text, sticker=None):
    channels = await get_active_channels()
    for ch in set(channels + [str(ADMIN_ID)]):
        try:
            if sticker: 
                try:
                    await bot.send_sticker(chat_id=ch, sticker=sticker)
                except:
                    pass
            await bot.send_message(chat_id=ch, text=text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Failed to send to {ch}: {e}")

async def automation_worker(bot):
    global is_global_running
    logger.info("Global Engine Started!")
    last_predicted_period = None
    
    while is_global_running:
        try:
            current_period, seconds = await get_wingo_data()
            if seconds >= 45:
                await asyncio.sleep(2)
                continue

            if current_period and current_period != last_predicted_period:
                p_size, p_nums = await get_next_prediction()
                last_predicted_period = current_period
                
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("INSERT INTO history (period, size, nums, status) VALUES (?, ?, ?, 'WAITING')", (current_period, p_size, p_nums))
                    await db.commit()
                
                g_link = await get_setting("GAME_LINK") or "Not Set"
                b_link = await get_setting("BOT_LINK") or "Not Set"
                c_link = await get_setting("ADMIN_CHANNEL_LINK") or "Not Set"

                msg = (f"🔥 <b>ALI PREDICTION VIP</b> 🔥\n\n"
                       f"🎯 <b>NEW SIGNAL</b>\n\n"
                       f"<b>PERIOD:</b> <code>{current_period}</code>\n"
                       f"<b>📊 SIZE:</b> {p_size}\n"
                       f"<b>🔢 NUMBERS:</b> {p_nums}\n\n"
                       f"⚠️ <i>Trend Analytical Prediction</i>\n\n"
                       f"━━━━━━━━━━━━━━━━\n"
                       f"🎮 <b>Play Here:</b> {g_link}\n"
                       f"🤖 <b>Bot Link:</b> {b_link}\n"
                       f"📢 <b>Join Channel:</b> {c_link}")
                
                start_stk = await get_setting("START_STICKER")
                await broadcast_to_channels(bot, msg, start_stk)
                
                await asyncio.sleep(55 - seconds)
                
                actual_size = random.choice(["BIG", "SMALL"])
                is_win = (p_size == actual_size)
                win_loss = "WIN" if is_win else "LOSS"
                
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE history SET result_size=?, status='DONE', win_loss=? WHERE period=?", (actual_size, win_loss, current_period))
                    await db.commit()

                res_msg = (f"🏆 <b>RESULT VIP</b>\n\n"
                           f"<b>PERIOD:</b> <code>{current_period}</code>\n"
                           f"<b>🎯 PREDICTED:</b> {p_size} ({p_nums})\n"
                           f"<b>🎲 RESULT:</b> {actual_size}\n\n"
                           f"<b>STATUS: {win_loss}</b>")

                win_stk = await get_setting("WIN_STICKER")
                loss_stk = await get_setting("LOSS_STICKER")
                final_stk = win_stk if is_win else loss_stk
                await broadcast_to_channels(bot, res_msg, final_stk)

        except Exception as e:
            logger.error(f"Loop Error: {e}")
            await asyncio.sleep(5)

# ==========================================
# 📱 HANDLERS & MENUS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (uid) VALUES (?)", (user_id,))
        await db.commit()
        async with db.execute("SELECT status FROM users WHERE uid=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            status = row[0]

    if user_id == ADMIN_ID:
        await update.message.reply_text("👋 Hello Admin! Type /admin to access panel.")
        return

    if status == 'BLOCKED':
        await update.message.reply_text("⛔ You are blocked by Admin.")
    elif status == 'NEW' or status == 'PENDING':
        g_link = await get_setting("GAME_LINK") or "Contact Admin"
        msg = (f"👋 <b>Welcome to Ali Prediction VIP</b>\n\n"
               f"📜 <b>RULES:</b>\n"
               f"1. Create account using our link.\n"
               f"2. Deposit funds.\n"
               f"3. Send your Game UID here to get approved.\n\n"
               f"🔗 <b>Game Link:</b> {g_link}\n\n"
               f"👉 <i>Please reply with your Game UID to request activation:</i>")
        user_states[user_id] = "WAITING_FOR_UID"
        await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
    elif status == 'ACTIVE':
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Add My Channel", callback_data="user_add_channel")],
            [InlineKeyboardButton("▶ Start Channel Signals", callback_data="user_start_channel")],
            [InlineKeyboardButton("⏹ Stop Channel Signals", callback_data="user_stop_channel")]
        ])
        await update.message.reply_text("🔥 <b>ALI PREDICTION VIP USER PANEL</b> 🔥\n\nYou are Active! Manage your channel below.", reply_markup=kb, parse_mode="HTML")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    user_states[user_id] = "WAITING_ADMIN_PASSWORD"
    await update.message.reply_text("🔒 <b>Please enter Admin Password:</b>", parse_mode="HTML")

def admin_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶ START GLOBAL", callback_data="adm_start"), InlineKeyboardButton("⏹ STOP GLOBAL", callback_data="adm_stop")],
        [InlineKeyboardButton("🖼 Set Stickers", callback_data="adm_stickers"), InlineKeyboardButton("🔗 Set Links", callback_data="adm_links")],
        [InlineKeyboardButton("👥 User Management", callback_data="adm_users"), InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")]
    ])

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_global_running, automation_task
    query = update.callback_query
    uid = update.effective_user.id
    await query.answer()
    data = query.data

    if uid == ADMIN_ID:
        if data == "adm_main":
            await query.edit_message_text("⚙️ <b>ADMIN PANEL</b>", reply_markup=admin_main_kb(), parse_mode="HTML")
        elif data == "adm_start":
            if is_global_running: return await query.answer("Already Running!")
            is_global_running = True
            automation_task = asyncio.create_task(automation_worker(context.bot))
            await query.edit_message_text("🟢 GLOBAL SIGNALS STARTED!", reply_markup=admin_main_kb())
        elif data == "adm_stop":
            is_global_running = False
            if automation_task: automation_task.cancel()
            await query.edit_message_text("⏹ GLOBAL SIGNALS STOPPED!", reply_markup=admin_main_kb())
        elif data == "adm_stickers":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Set WIN", callback_data="stk_WIN_STICKER"), InlineKeyboardButton("Set LOSS", callback_data="stk_LOSS_STICKER")],
                [InlineKeyboardButton("Set START", callback_data="stk_START_STICKER"), InlineKeyboardButton("Set STOP", callback_data="stk_STOP_STICKER")],
                [InlineKeyboardButton("🔙 Back", callback_data="adm_main")]
            ])
            await query.edit_message_text("🖼 <b>Select sticker to set:</b>", reply_markup=kb, parse_mode="HTML")
        elif data.startswith("stk_"):
            key = data.replace("stk_", "")
            user_states[uid] = f"WAITING_{key}"
            await query.edit_message_text(f"Please send the {key} sticker now:")
        elif data == "adm_links":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Set Game Link", callback_data="lnk_GAME_LINK")],
                [InlineKeyboardButton("Set Bot Link", callback_data="lnk_BOT_LINK")],
                [InlineKeyboardButton("Set Admin Channel", callback_data="lnk_ADMIN_CHANNEL_LINK")],
                [InlineKeyboardButton("🔙 Back", callback_data="adm_main")]
            ])
            await query.edit_message_text("🔗 <b>Select link to update:</b>", reply_markup=kb, parse_mode="HTML")
        elif data.startswith("lnk_"):
            key = data.replace("lnk_", "")
            user_states[uid] = f"WAITING_{key}"
            await query.edit_message_text(f"Please send the URL for {key}:")
        elif data == "adm_users":
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute("SELECT uid, game_uid FROM users WHERE status='PENDING'") as cursor:
                    pending = await cursor.fetchall()
            if not pending:
                return await query.edit_message_text("No pending users.", reply_markup=admin_main_kb())
            kb = []
            for u, g_uid in pending:
                kb.append([InlineKeyboardButton(f"UID: {g_uid} (Approve)", callback_data=f"usr_app_{u}"),
                           InlineKeyboardButton("Block", callback_data=f"usr_blk_{u}")])
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="adm_main")])
            await query.edit_message_text("👥 <b>Pending Users:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        elif data.startswith("usr_app_"):
            u = int(data.split("_")[2])
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE users SET status='ACTIVE' WHERE uid=?", (u,))
                await db.commit()
            await context.bot.send_message(chat_id=u, text="🎉 Your account has been ACTIVATED! Send /start to access the panel.")
            await query.edit_message_text(f"User {u} Approved.", reply_markup=admin_main_kb())
        elif data.startswith("usr_blk_"):
            u = int(data.split("_")[2])
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE users SET status='BLOCKED' WHERE uid=?", (u,))
                await db.commit()
            await query.edit_message_text(f"User {u} Blocked.", reply_markup=admin_main_kb())
        elif data == "adm_broadcast":
            user_states[uid] = "WAITING_BROADCAST"
            await query.edit_message_text("📢 Send the message/image you want to broadcast to all users:")

    else:
        if data == "user_add_channel":
            user_states[uid] = "WAITING_USER_CHANNEL"
            await query.edit_message_text("Make the bot Admin in your channel, then send your Channel ID (e.g. -100123...):")
        elif data == "user_start_channel":
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE channels SET is_running=1 WHERE owner_uid=?", (uid,))
                await db.commit()
            await query.answer("✅ Channel Signals Started!", show_alert=True)
        elif data == "user_stop_channel":
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE channels SET is_running=0 WHERE owner_uid=?", (uid,))
                await db.commit()
            await query.answer("⏹ Channel Signals Stopped!", show_alert=True)

async def text_sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_states.get(uid)
    if not state: return

    if uid == ADMIN_ID:
        if state == "WAITING_ADMIN_PASSWORD":
            if update.message.text == ADMIN_PASSWORD:
                user_states.pop(uid)
                await update.message.reply_text("✅ Password Correct!\n\n⚙️ <b>ADMIN PANEL</b>", reply_markup=admin_main_kb(), parse_mode="HTML")
            else:
                await update.message.reply_text("❌ Wrong Password.")
                
        elif state.startswith("WAITING_") and "STICKER" in state:
            if update.message.sticker:
                key = state.replace("WAITING_", "")
                await set_setting(key, update.message.sticker.file_id)
                user_states.pop(uid)
                await update.message.reply_text(f"✅ {key} Saved!", reply_markup=admin_main_kb())

        elif state.startswith("WAITING_") and "LINK" in state:
            key = state.replace("WAITING_", "")
            await set_setting(key, update.message.text)
            user_states.pop(uid)
            await update.message.reply_text(f"✅ {key} Saved!", reply_markup=admin_main_kb())

        elif state == "WAITING_BROADCAST":
            user_states.pop(uid)
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute("SELECT uid FROM users WHERE status='ACTIVE'") as cursor:
                    users = await cursor.fetchall()
            count = 0
            for u in users:
                try:
                    await update.message.copy(chat_id=u[0])
                    count += 1
                except: pass
            await update.message.reply_text(f"✅ Broadcast sent to {count} active users.", reply_markup=admin_main_kb())

    else:
        if state == "WAITING_FOR_UID":
            game_uid = update.message.text
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE users SET game_uid=?, status='PENDING' WHERE uid=?", (game_uid, uid))
                await db.commit()
            user_states.pop(uid)
            await update.message.reply_text("✅ Your UID has been sent to the Admin. Please wait for approval.")
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 New User Registration!\nTelegram ID: {uid}\nGame UID: {game_uid}\n\nCheck User Management to Approve.")
            
        elif state == "WAITING_USER_CHANNEL":
            channel_id = update.message.text
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("INSERT OR REPLACE INTO channels (owner_uid, channel_id) VALUES (?, ?)", (uid, channel_id))
                await db.commit()
            user_states.pop(uid)
            await update.message.reply_text("✅ Channel Saved! Now you can start signals in your channel by typing /start.")

# ==========================================
# 🚀 MAIN RUNNER
# ==========================================
def main():
    # START DUMMY SERVER FOR RAILWAY
    keep_alive()

    # BUILD APP (PTB v20)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, text_sticker_handler))
    
    logger.info("Bot is Running! Background Railway Server is ACTIVE.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
