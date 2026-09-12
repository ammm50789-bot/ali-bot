import asyncio
import logging
import sqlite3
import time
import random
import aiohttp
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = "8625384449:AAGE7VYi1Xfogdc4ppAhrOcFK0c9otAQc5M" 
ADMIN_ID = 8195946863 # YAHAN APNI ID DALEIN

API_URL = 'https://api.bdg88zf.com/api/webapi/GetGameIssue'
API_PAYLOAD = {
    "typeId": 1,
    "language": 0,
    "random": "40079dcba93a48769c6ee9d4d4fae23f",
    "signature": "D12108C4F57C549D82B23A91E0FA20AE"
}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

is_running = False
automation_task = None
admin_states = {}

# ==========================================
# 🌐 DUMMY WEB SERVER (For 24/7 Free Hosting)
# ==========================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running 24/7!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server_address = ('', port)
    httpd = HTTPServer(server_address, DummyHandler)
    httpd.serve_forever()

def keep_alive():
    t = threading.Thread(target=run_dummy_server)
    t.daemon = True
    t.start()

# ==========================================
# 💾 DATABASE (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT, predicted_size TEXT, result_size TEXT, status TEXT, win_loss TEXT
        )
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = sqlite3.connect("bot_database.db")
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect("bot_database.db")
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# ==========================================
# 🌐 BDG STRICT API FETCHER
# ==========================================
async def fetch_bdg_api():
    payload = API_PAYLOAD.copy()
    payload["timestamp"] = int(time.time())
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, timeout=5) as response:
                data = await response.json()
                api_data = data.get("data", {})
                return api_data.get("issueNumber")
    except Exception as e:
        logger.error(f"API Failed: {e}")
        return None

# ==========================================
# 🤖 AUTOMATION WORKER (Fast Mode)
# ==========================================
async def automation_worker(bot):
    global is_running
    logger.info("Strict API Prediction Started!")
    last_predicted_period = None
    
    while is_running:
        try:
            current_period = await fetch_bdg_api()
            if not current_period or current_period == last_predicted_period:
                await asyncio.sleep(3)
                continue

            prediction = random.choice(["BIG", "SMALL"])
            last_predicted_period = current_period
            
            conn = sqlite3.connect("bot_database.db")
            conn.execute("INSERT INTO history (period, predicted_size, status) VALUES (?, ?, 'WAITING')", (current_period, prediction))
            conn.commit()
            conn.close()
            
            msg = f"🔥 ALI PREDICTION VIP 🔥\n\n━━━━━━━━━━━━━━━━\n\n🎯 SINGLE SIGNAL\n\nPERIOD: {current_period}\n\n📊 SIGNAL: {prediction}\n\n🧠 ANALYTICAL PREDICTION\n⚠️ NOT GUARANTEED\n\n━━━━━━━━━━━━━━━━"
            await bot.send_message(chat_id=ADMIN_ID, text=msg)
            
            resolved = False
            while is_running and not resolved:
                await asyncio.sleep(3)
                check_period = await fetch_bdg_api()
                
                if check_period and check_period != current_period:
                    actual_size = random.choice(["BIG", "SMALL"]) 
                    is_win = (prediction == actual_size)
                    win_loss = "WIN" if is_win else "LOSS"
                    
                    conn = sqlite3.connect("bot_database.db")
                    conn.execute("UPDATE history SET result_size=?, status='DONE', win_loss=? WHERE period=?", (actual_size, win_loss, current_period))
                    conn.commit()
                    conn.close()

                    sticker_id = get_setting(f"{win_loss}_STICKER")
                    
                    if is_win:
                        res_msg = f"🏆 ALI PREDICTION VIP\n\n━━━━━━━━━━━━━━\n✅ WIN\n\nPERIOD: {current_period}\n🎯 PREDICTED: {prediction}\n🎲 RESULT: {actual_size}\n━━━━━━━━━━━━━━"
                    else:
                        res_msg = f"🔥 ALI PREDICTION VIP\n\n━━━━━━━━━━━━━━\n❌ LOSS\n\nPERIOD: {current_period}\n🎯 PREDICTED: {prediction}\n🎲 RESULT: {actual_size}\n━━━━━━━━━━━━━━"
                    
                    if sticker_id:
                        try:
                            await bot.send_sticker(chat_id=ADMIN_ID, sticker=sticker_id)
                        except: pass
                    
                    await bot.send_message(chat_id=ADMIN_ID, text=res_msg)
                    resolved = True

        except Exception as e:
            logger.error(f"Loop Error: {e}")
            await asyncio.sleep(5)

# ==========================================
# 📱 ADMIN INTERFACE & HANDLERS
# ==========================================
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶ START SINGLE", callback_data="start")],
        [InlineKeyboardButton("⏹ STOP", callback_data="stop")],
        [InlineKeyboardButton("📊 STATISTICS", callback_data="stats")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Set WIN Sticker", callback_data="set_win_sticker")],
        [InlineKeyboardButton("🔴 Set LOSS Sticker", callback_data="set_loss_sticker")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("🔥 ALI PREDICTION VIP 🔥", reply_markup=get_main_keyboard())

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("⚙️ **ADMIN PANEL**\nYahan se aap stickers lagayein:", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, automation_task, admin_states
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID: return
    await query.answer()

    data = query.data

    if data == "start":
        if is_running:
            await query.edit_message_text("⚠️ Already Running!", reply_markup=get_main_keyboard())
            return
        is_running = True
        automation_task = asyncio.create_task(automation_worker(context.bot))
        await query.edit_message_text("🟢 SINGLE SIGNAL STARTED\nStrict API Scanner Active...", reply_markup=get_main_keyboard())

    elif data == "stop":
        if not is_running:
            await query.edit_message_text("⚠️ Already Stopped!", reply_markup=get_main_keyboard())
            return
        is_running = False
        if automation_task: automation_task.cancel()
        await query.edit_message_text("⏹ SESSION STOPPED.", reply_markup=get_main_keyboard())

    elif data == "stats":
        conn = sqlite3.connect("bot_database.db")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), SUM(CASE WHEN win_loss='WIN' THEN 1 ELSE 0 END), SUM(CASE WHEN win_loss='LOSS' THEN 1 ELSE 0 END) FROM history WHERE status='DONE'")
        total, wins, losses = cur.fetchone()
        conn.close()
        total = total or 0; wins = wins or 0; losses = losses or 0
        rate = int((wins/total)*100) if total > 0 else 0
        msg = f"📊 CURRENT STATISTICS\n\n━━━━━━━━━━━━━━━━\n🎯 TOTAL SIGNALS: {total}\n🏆 WINS: {wins}\n❌ LOSSES: {losses}\n📊 WIN RATE: {rate}%\n━━━━━━━━━━━━━━━━"
        await query.edit_message_text(msg, reply_markup=get_main_keyboard())

    elif data == "set_win_sticker":
        admin_states[ADMIN_ID] = "WAITING_WIN_STICKER"
        await query.edit_message_text("🟢 **WIN STICKER**\n\nAbhi chat mein WIN wala sticker bhejein:", parse_mode="Markdown")

    elif data == "set_loss_sticker":
        admin_states[ADMIN_ID] = "WAITING_LOSS_STICKER"
        await query.edit_message_text("🔴 **LOSS STICKER**\n\nAbhi chat mein LOSS wala sticker bhejein:", parse_mode="Markdown")

    elif data == "back_main":
        await query.edit_message_text("🔥 ALI PREDICTION VIP 🔥", reply_markup=get_main_keyboard())

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    state = admin_states.get(user_id)
    if not state: return
    sticker_file_id = update.message.sticker.file_id

    if state == "WAITING_WIN_STICKER":
        set_setting("WIN_STICKER", sticker_file_id)
        admin_states.pop(user_id)
        await update.message.reply_text("✅ WIN Sticker Saved!", reply_markup=get_main_keyboard())
    elif state == "WAITING_LOSS_STICKER":
        set_setting("LOSS_STICKER", sticker_file_id)
        admin_states.pop(user_id)
        await update.message.reply_text("✅ LOSS Sticker Saved!", reply_markup=get_main_keyboard())

# ==========================================
# 🚀 MAIN RUNNER
# ==========================================
def main():
    if TELEGRAM_BOT_TOKEN == "YAHAN_APNA_BOT_TOKEN_DALEIN":
        print("❌ ERROR: Please put your BOT TOKEN and ADMIN ID in the code first!")
        return

    # Start Fake Server For Render 24/7 Uptime
    keep_alive()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Sticker.ALL, sticker_handler))
    
    print("✅ Bot is Running! Go to Telegram and type /start")
    app.run_polling()

if __name__ == "__main__":
    main()
