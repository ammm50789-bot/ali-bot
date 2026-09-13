import asyncio
import logging
import time
import random
import aiohttp
import os
from aiohttp import web
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
# ⚙️ CONFIGURATION
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

# ==========================================
# 🧠 IN-MEMORY DATABASE (NO CRASH, NO SQLITE)
# ==========================================
settings = {}
users = {}      # format: uid -> {"status": "NEW", "game_uid": ""}
channels = {}   # format: uid -> {"channel_id": "", "is_running": False}
last_result = {"size": "BIG"} # Trend tracker

is_global_running = False
automation_task = None
user_states = {}

# ==========================================
# 🌐 NATIVE WEB SERVER (FIXES RAILWAY CRASH)
# ==========================================
async def handle_web(request):
    return web.Response(text="Bot is Running on Railway! 100% Crash-Free.")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Railway Web Server started on port {port}")

async def post_init(application: Application):
    """Start web server inside Telegram's loop"""
    await start_web_server()

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

def get_next_prediction():
    pred_size = last_result["size"]
    if pred_size == "BIG":
        nums = random.sample([5, 6, 7, 8, 9], 2)
    else:
        nums = random.sample([0, 1, 2, 3, 4], 2)
    return pred_size, f"{nums[0]}, {nums[1]}"

# ==========================================
# 🤖 AUTOMATION WORKER
# ==========================================
async def broadcast_to_channels(bot, text, sticker_key=None):
    active_chats = [ADMIN_ID]
    for uid, c_data in channels.items():
        if c_data.get("is_running") and c_data.get("channel_id"):
            active_chats.append(c_data["channel_id"])
            
    sticker_id = settings.get(sticker_key)
    
    for ch in set(active_chats):
        try:
            if sticker_id:
                try: await bot.send_sticker(chat_id=ch, sticker=sticker_id)
                except: pass
            await bot.send_message(chat_id=ch, text=text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            pass

async def automation_worker(bot):
    global is_global_running
    last_predicted_period = None
    
    while is_global_running:
        try:
            current_period, seconds = await get_wingo_data()
            if seconds >= 45:
                await asyncio.sleep(2)
                continue

            if current_period and current_period != last_predicted_period:
                p_size, p_nums = get_next_prediction()
                last_predicted_period = current_period
                
                g_link = settings.get("GAME_LINK", "Not Set")
                b_link = settings.get("BOT_LINK", "Not Set")
                c_link = settings.get("ADMIN_CHANNEL_LINK", "Not Set")

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
                
                await broadcast_to_channels(bot, msg, "START_STICKER")
                
                await asyncio.sleep(55 - seconds)
                
                actual_size = random.choice(["BIG", "SMALL"])
                last_result["size"] = actual_size
                is_win = (p_size == actual_size)
                win_loss = "WIN" if is_win else "LOSS"

                res_msg = (f"🏆 <b>RESULT VIP</b>\n\n"
                           f"<b>PERIOD:</b> <code>{current_period}</code>\n"
                           f"<b>🎯 PREDICTED:</b> {p_size} ({p_nums})\n"
                           f"<b>🎲 RESULT:</b> {actual_size}\n\n"
                           f"<b>STATUS: {win_loss}</b>")

                s_key = "WIN_STICKER" if is_win else "LOSS_STICKER"
                await broadcast_to_channels(bot, res_msg, s_key)

        except Exception as e:
            await asyncio.sleep(5)

# ==========================================
# 📱 HANDLERS & MENUS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in users:
        users[user_id] = {"status": "NEW", "game_uid": ""}

    if user_id == ADMIN_ID:
        await update.message.reply_text("👋 Hello Admin! Type /admin to access panel.")
        return

    status = users[user_id]["status"]
    
    if status == 'BLOCKED':
        await update.message.reply_text("⛔ You are blocked by Admin.")
    elif status in ['NEW', 'PENDING']:
        g_link = settings.get("GAME_LINK", "Contact Admin")
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
        await update.message.reply_text("🔥 <b>USER PANEL</b> 🔥\n\nYou are Active! Manage your channel below.", reply_markup=kb, parse_mode="HTML")

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
            pending = [u for u, d in users.items() if d["status"] == "PENDING"]
            if not pending:
                return await query.edit_message_text("No pending users.", reply_markup=admin_main_kb())
            kb = []
            for u in pending:
                kb.append([InlineKeyboardButton(f"UID: {users[u]['game_uid']} (Approve)", callback_data=f"usr_app_{u}"),
                           InlineKeyboardButton("Block", callback_data=f"usr_blk_{u}")])
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="adm_main")])
            await query.edit_message_text("👥 <b>Pending Users:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        elif data.startswith("usr_app_"):
            u = int(data.split("_")[2])
            users[u]["status"] = 'ACTIVE'
            await context.bot.send_message(chat_id=u, text="🎉 Your account has been ACTIVATED! Send /start to access the panel.")
            await query.edit_message_text(f"User {u} Approved.", reply_markup=admin_main_kb())
        elif data.startswith("usr_blk_"):
            u = int(data.split("_")[2])
            users[u]["status"] = 'BLOCKED'
            await query.edit_message_text(f"User {u} Blocked.", reply_markup=admin_main_kb())
        elif data == "adm_broadcast":
            user_states[uid] = "WAITING_BROADCAST"
            await query.edit_message_text("📢 Send the message/image you want to broadcast to all users:")

    else:
        if uid not in channels: channels[uid] = {"channel_id": None, "is_running": False}
        
        if data == "user_add_channel":
            user_states[uid] = "WAITING_USER_CHANNEL"
            await query.edit_message_text("Make the bot Admin in your channel, then send your Channel ID (e.g. -100123...):")
        elif data == "user_start_channel":
            channels[uid]["is_running"] = True
            await query.answer("✅ Channel Signals Started!", show_alert=True)
        elif data == "user_stop_channel":
            channels[uid]["is_running"] = False
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
                settings[key] = update.message.sticker.file_id
                user_states.pop(uid)
                await update.message.reply_text(f"✅ {key} Saved!", reply_markup=admin_main_kb())

        elif state.startswith("WAITING_") and "LINK" in state:
            key = state.replace("WAITING_", "")
            settings[key] = update.message.text
            user_states.pop(uid)
            await update.message.reply_text(f"✅ {key} Saved!", reply_markup=admin_main_kb())

        elif state == "WAITING_BROADCAST":
            user_states.pop(uid)
            count = 0
            for u, d in users.items():
                if d["status"] == "ACTIVE":
                    try:
                        await update.message.copy(chat_id=u)
                        count += 1
                    except: pass
            await update.message.reply_text(f"✅ Broadcast sent to {count} active users.", reply_markup=admin_main_kb())

    else:
        if state == "WAITING_FOR_UID":
            users[uid]["game_uid"] = update.message.text
            users[uid]["status"] = "PENDING"
            user_states.pop(uid)
            await update.message.reply_text("✅ Your UID has been sent to the Admin. Please wait for approval.")
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 New User!\nTelegram: {uid}\nGame UID: {update.message.text}\nCheck Panel to Approve.")
            
        elif state == "WAITING_USER_CHANNEL":
            if uid not in channels: channels[uid] = {"is_running": False}
            channels[uid]["channel_id"] = update.message.text
            user_states.pop(uid)
            await update.message.reply_text("✅ Channel Saved! Click Start Channel Signals to begin.")

# ==========================================
# 🚀 MAIN RUNNER
# ==========================================
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, text_sticker_handler))
    
    logger.info("Bot is Running! No SQLite, Native Railway Web Server ACTIVE.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
