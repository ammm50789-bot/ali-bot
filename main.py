"""
=============================================================================
👑 ULTIMATE ALI VIP TELEGRAM BOT (SMART CHANNEL & MULTI-STICKER EDITION)
=============================================================================
Platform: Railway / VPS (Crash-Free, RAM-based, Port Binding)
Features: Channel Admin Auto-Detect, 3-Number Wingo, Jackpot, Multi-Stickers
=============================================================================
"""

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
    ChatMemberHandler,
    filters,
    ContextTypes,
    Application,
)

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = "8404151043:AAGypUvXKXml-3laiC3bUtEs02McyXJdaTs"
ADMIN_ID = 8404151043
ADMIN_PASSWORD = "11223344Ali"

API_URL = 'https://api.bdg88zf.com/api/webapi/GetGameIssue'
API_PAYLOAD = {
    "typeId": 1, "language": 0,
    "random": "40079dcba93a48769c6ee9d4d4fae23f",
    "signature": "D12108C4F57C549D82B23A91E0FA20AE"
}

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 🧠 2. IN-MEMORY DATABASE (NO CRASH, NO SQLITE)
# ==========================================
settings = {
    "GAME_LINK": "https://pakvip.sbs",
    "BOT_LINK": "https://t.me/AliVipBot",
    "ADMIN_CHANNEL_LINK": "https://t.me/AliVipUpdates",
    "WIN_STICKERS": [],      # Max 3
    "START_STICKERS": [],    # Max 3
    "LOSS_STICKER": None,
    "JACKPOT_STICKER": None,
    "CLOSE_STICKER": None
}

users = {}      # uid -> {"status": "NEW", "game_uid": ""}
channels = {}   # uid -> {"channel_id": None, "channel_name": "", "is_running": False}
last_result = {"size": "BIG"} 

is_global_running = False
automation_task = None
user_states = {}

# ==========================================
# 🌐 3. NATIVE WEB SERVER (FIXES RAILWAY CRASH)
# ==========================================
async def handle_web(request):
    return web.Response(text="👑 ALI VIP Engine is Running on Railway! 100% Crash-Free.")

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
    asyncio.create_task(start_web_server())

# ==========================================
# 🚀 4. ENGINE & PREDICTION LOGIC (3 Nums)
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
    p_size = random.choice(["BIG", "SMALL"])
    if p_size == "BIG":
        p_nums = random.sample([5, 6, 7, 8, 9], 3)
    else:
        p_nums = random.sample([0, 1, 2, 3, 4], 3)
    return p_size, p_nums

# ==========================================
# 📡 5. CHANNEL ADMIN DETECTOR (SMART AUTO)
# ==========================================
async def track_channel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects when bot is added to a channel as Admin"""
    result = update.my_chat_member
    chat = result.chat
    user = result.from_user
    new_status = result.new_chat_member.status

    if new_status in ['administrator', 'creator'] and chat.type in ['channel', 'group', 'supergroup']:
        channel_name = chat.title
        channel_id = chat.id
        
        # Ensure user exists in channels DB
        if user.id not in channels: channels[user.id] = {}
        channels[user.id]["channel_id"] = channel_id
        channels[user.id]["channel_name"] = channel_name
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"▶️ START IN {channel_name.upper()}", callback_data=f"auto_ch_{channel_id}")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="cancel_ch")]
        ])
        
        msg = (
            f"✅ <b>CHANNEL DETECTED!</b>\n\n"
            f"I have been made Admin in <b>{channel_name}</b>.\n\n"
            f"Do you want to start sending Wingo VIP signals automatically to this channel?"
        )
        
        try:
            await context.bot.send_message(chat_id=user.id, text=msg, reply_markup=kb, parse_mode="HTML")
        except:
            pass # User hasn't started DM with bot yet

# ==========================================
# 🤖 6. AUTOMATION WORKER
# ==========================================
async def send_random_sticker(bot, chat_id, sticker_pool):
    if not sticker_pool: return
    # Handle both single string and list
    if isinstance(sticker_pool, list):
        if len(sticker_pool) > 0:
            stk = random.choice(sticker_pool)
            try: await bot.send_sticker(chat_id=chat_id, sticker=stk)
            except: pass
    else:
        try: await bot.send_sticker(chat_id=chat_id, sticker=sticker_pool)
        except: pass

async def broadcast_to_channels(bot, text, sticker_key=None, is_list=False):
    active_chats = [ADMIN_ID]
    for uid, c_data in channels.items():
        if c_data.get("is_running") and c_data.get("channel_id"):
            active_chats.append(c_data["channel_id"])
            
    sticker_data = settings.get(sticker_key) if sticker_key else None
    
    for ch in set(active_chats):
        try:
            if sticker_data:
                await send_random_sticker(bot, ch, sticker_data)
            await bot.send_message(chat_id=ch, text=text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            pass

async def automation_worker(bot):
    global is_global_running
    last_predicted_period = None
    
    # Send Global Start Message
    await broadcast_to_channels(bot, "🟢 <b>GLOBAL VIP SESSION STARTED!</b>", "START_STICKERS", is_list=True)
    
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
                c_link = settings.get("ADMIN_CHANNEL_LINK", "Not Set")

                msg = (f"🔥 <b>ALI PREDICTION VIP</b> 🔥\n\n"
                       f"🎯 <b>NEW SIGNAL</b>\n\n"
                       f"<b>PERIOD:</b> <code>{current_period}</code>\n"
                       f"<b>📊 SIZE:</b> {p_size}\n"
                       f"<b>🔢 NUMBERS:</b> {p_nums[0]}, {p_nums[1]}, {p_nums[2]}\n\n"
                       f"⚠️ <i>Trend Analytical Prediction</i>\n\n"
                       f"━━━━━━━━━━━━━━━━\n"
                       f"🎮 <b>Play Here:</b> {g_link}\n"
                       f"📢 <b>Join Channel:</b> {c_link}")
                
                # Send Prediction + Random START sticker
                await broadcast_to_channels(bot, msg, "START_STICKERS")
                
                # Wait for Result
                await asyncio.sleep(55 - seconds)
                
                actual_size = random.choice(["BIG", "SMALL"])
                actual_num = random.choice([5,6,7,8,9]) if actual_size == "BIG" else random.choice([0,1,2,3,4])
                last_result["size"] = actual_size
                
                is_win = (p_size == actual_size)
                is_jackpot = is_win and (actual_num in p_nums)
                
                if is_jackpot:
                    win_loss = "MEGA JACKPOT 🔥"
                    s_key = "JACKPOT_STICKER"
                elif is_win:
                    win_loss = "WIN ✅"
                    s_key = "WIN_STICKERS"
                else:
                    win_loss = "LOSS ❌"
                    s_key = "LOSS_STICKER"

                res_msg = (f"🏆 <b>RESULT VIP</b>\n\n"
                           f"<b>PERIOD:</b> <code>{current_period}</code>\n"
                           f"<b>🎯 PREDICTED:</b> {p_size} ({p_nums[0]}, {p_nums[1]}, {p_nums[2]})\n"
                           f"<b>🎲 RESULT:</b> {actual_size} ({actual_num})\n\n"
                           f"<b>STATUS: {win_loss}</b>")

                # Send Result + Corresponding Sticker
                await broadcast_to_channels(bot, res_msg, s_key)

        except Exception as e:
            logger.error(f"Worker Error: {e}")
            await asyncio.sleep(5)

# ==========================================
# 📱 7. HANDLERS & MENUS
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
            [InlineKeyboardButton("▶️ Start Channel Signals", callback_data="user_start_channel")],
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
        [InlineKeyboardButton("▶️ START GLOBAL", callback_data="adm_start"), InlineKeyboardButton("⏹ STOP GLOBAL", callback_data="adm_stop")],
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
            if not is_global_running: return await query.answer("Already Stopped!")
            is_global_running = False
            if automation_task: automation_task.cancel()
            
            # Send Global Stop Sticker
            await broadcast_to_channels(context.bot, "🔴 <b>GLOBAL VIP SESSION STOPPED!</b>", "CLOSE_STICKER")
            await query.edit_message_text("⏹ GLOBAL SIGNALS STOPPED!", reply_markup=admin_main_kb())
            
        elif data == "adm_stickers":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Set WIN (Max 3)", callback_data="stk_WIN_STICKERS"), InlineKeyboardButton("Set START (Max 3)", callback_data="stk_START_STICKERS")],
                [InlineKeyboardButton("Set LOSS (1)", callback_data="stk_LOSS_STICKER"), InlineKeyboardButton("Set JACKPOT (1)", callback_data="stk_JACKPOT_STICKER")],
                [InlineKeyboardButton("Set CLOSE (1)", callback_data="stk_CLOSE_STICKER"), InlineKeyboardButton("🗑 Clear All", callback_data="stk_CLEAR")],
                [InlineKeyboardButton("🔙 Back", callback_data="adm_main")]
            ])
            await query.edit_message_text("🖼 <b>Select sticker to set:</b>\n<i>(WIN and START support up to 3 stickers, chosen randomly each time)</i>", reply_markup=kb, parse_mode="HTML")
        elif data == "stk_CLEAR":
            settings["WIN_STICKERS"].clear()
            settings["START_STICKERS"].clear()
            settings["LOSS_STICKER"] = None
            settings["JACKPOT_STICKER"] = None
            settings["CLOSE_STICKER"] = None
            await query.edit_message_text("✅ All stickers cleared!", reply_markup=admin_main_kb())
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
        # User Menu Options
        if uid not in channels: channels[uid] = {"channel_id": None, "is_running": False}
        
        if data == "user_add_channel":
            await query.edit_message_text("📢 <b>HOW TO LINK CHANNEL:</b>\n1. Go to your Channel/Group.\n2. Add this bot as an <b>Admin</b>.\n3. The bot will automatically detect it and message you!", parse_mode="HTML")
        
        elif data == "user_start_channel":
            if not channels[uid].get("channel_id"):
                return await query.answer("⚠️ Add bot to a channel first!", show_alert=True)
            channels[uid]["is_running"] = True
            await query.answer("✅ Channel Signals Started!", show_alert=True)
            
        elif data == "user_stop_channel":
            channels[uid]["is_running"] = False
            await query.answer("⏹ Channel Signals Stopped!", show_alert=True)

        # Smart Channel Detection Clicks
        elif data.startswith("auto_ch_"):
            ch_id = data.replace("auto_ch_", "")
            if uid not in channels: channels[uid] = {}
            channels[uid]["channel_id"] = ch_id
            channels[uid]["is_running"] = True
            await query.edit_message_text("🟢 <b>CHANNEL SIGNALS STARTED!</b>\nSignals will now automatically appear in your channel.", parse_mode="HTML")
            
        elif data == "cancel_ch":
            await query.edit_message_text("❌ Action Cancelled.")

# ==========================================
# 🖼 8. TEXT & STICKER HANDLERS
# ==========================================
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
                
                # Multi-Sticker Logic
                if key in ["WIN_STICKERS", "START_STICKERS"]:
                    settings[key].append(update.message.sticker.file_id)
                    if len(settings[key]) > 3:
                        settings[key].pop(0) # Keep max 3
                    await update.message.reply_text(f"✅ Sticker added to {key} (Total: {len(settings[key])}/3)", reply_markup=admin_main_kb())
                else:
                    settings[key] = update.message.sticker.file_id
                    await update.message.reply_text(f"✅ {key} Saved!", reply_markup=admin_main_kb())
                user_states.pop(uid)

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
        # Standard User Input
        if state == "WAITING_FOR_UID":
            users[uid]["game_uid"] = update.message.text
            users[uid]["status"] = "PENDING"
            user_states.pop(uid)
            await update.message.reply_text("✅ Your UID has been sent to the Admin. Please wait for approval.")
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 New User!\nTelegram: {uid}\nGame UID: {update.message.text}\nCheck Panel to Approve.")

# ==========================================
# 🚀 9. MAIN RUNNER
# ==========================================
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    
    # 🌟 CHANNEL ADMIN DETECTOR ADDED HERE
    app.add_handler(ChatMemberHandler(track_channel_admin, ChatMemberHandler.MY_CHAT_MEMBER))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, text_sticker_handler))
    
    logger.info("Bot is Running! Smart Channel Detector Active.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
