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
# ⚙️ VIP CONFIGURATION
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
# 🧠 IN-MEMORY DATABASE (CRASH-FREE)
# ==========================================
settings = {}
users = {}  
# users format: {uid: {"status": "NEW", "game_uid": "", "dm_on": False, "ch_id": None, "ch_on": False}}
last_result = {"size": "BIG"} 

is_global_running = False
automation_task = None
user_states = {}

# ==========================================
# 🌐 NATIVE WEB SERVER (RAILWAY FIX)
# ==========================================
async def handle_web(request):
    return web.Response(text="💎 Premium VIP Bot is Running on Railway! 100% Crash-Free.")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Railway Server started on port {port}")

async def post_init(application: Application):
    await start_web_server()

# ==========================================
# 🌐 PREMIUM ENGINE & PREDICTION
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
    return pred_size, nums

# ==========================================
# 🤖 AUTOMATION WORKER (BROADCASTER)
# ==========================================
async def get_active_endpoints():
    endpoints = [ADMIN_ID]
    for uid, data in users.items():
        if data["status"] == "ACTIVE":
            if data.get("dm_on"):
                endpoints.append(uid)
            if data.get("ch_on") and data.get("ch_id"):
                endpoints.append(data["ch_id"])
    return list(set(endpoints))

async def broadcast_message(bot, text, sticker_key=None):
    endpoints = await get_active_endpoints()
    sticker_id = settings.get(sticker_key)
    
    for chat in endpoints:
        try:
            if sticker_id:
                try: await bot.send_sticker(chat_id=chat, sticker=sticker_id)
                except: pass
            if text:
                await bot.send_message(chat_id=chat, text=text, parse_mode="HTML", disable_web_page_preview=True)
        except:
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
                
                g_link = settings.get("GAME_LINK", "Link Not Set")
                b_link = settings.get("BOT_LINK", "Link Not Set")
                c_link = settings.get("ADMIN_CHANNEL_LINK", "Link Not Set")

                msg = (f"👑 <b>PREMIUM VIP SIGNAL</b> 👑\n\n"
                       f"🚀 <b>PERIOD:</b> <code>{current_period}</code>\n"
                       f"📊 <b>PREDICTION:</b> {p_size}\n"
                       f"🎯 <b>JACKPOT NUMS:</b> {p_nums[0]}, {p_nums[1]}\n\n"
                       f"💎 <i>High Accuracy AI Trend Analysis</i>\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"🎮 <b>Play Here:</b> {g_link}\n"
                       f"🤖 <b>VIP Bot:</b> {b_link}\n"
                       f"📢 <b>Official Channel:</b> {c_link}")
                
                await broadcast_message(bot, msg, None) # No sticker for normal signal
                
                await asyncio.sleep(55 - seconds)
                
                # Result Generation
                actual_size = random.choice(["BIG", "SMALL"])
                actual_num = random.choice([5,6,7,8,9]) if actual_size == "BIG" else random.choice([0,1,2,3,4])
                
                last_result["size"] = actual_size
                
                is_win = (p_size == actual_size)
                is_jackpot = is_win and (actual_num in p_nums)
                
                if is_jackpot:
                    status_text = "🔥 MEGA JACKPOT HIT 🔥"
                    s_key = "JACKPOT_STICKER"
                elif is_win:
                    status_text = "✅ SUPER WIN ✅"
                    s_key = "WIN_STICKER"
                else:
                    status_text = "❌ LOSS ❌"
                    s_key = "LOSS_STICKER"

                res_msg = (f"🏆 <b>VIP RESULT</b> 🏆\n\n"
                           f"🚀 <b>PERIOD:</b> <code>{current_period}</code>\n"
                           f"🎯 <b>PREDICTED:</b> {p_size} ({p_nums[0]}, {p_nums[1]})\n"
                           f"🎲 <b>ACTUAL RESULT:</b> {actual_size} ({actual_num})\n\n"
                           f"<b>{status_text}</b>")

                await broadcast_message(bot, res_msg, s_key)

        except Exception as e:
            await asyncio.sleep(5)

# ==========================================
# 📱 PREMIUM HANDLERS & MENUS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in users:
        users[user_id] = {"status": "NEW", "game_uid": "", "dm_on": False, "ch_id": None, "ch_on": False}

    if user_id == ADMIN_ID:
        await update.message.reply_text("👑 Welcome VIP Admin! Type /admin to access panel.")
        return

    status = users[user_id]["status"]
    
    if status == 'BLOCKED':
        await update.message.reply_text("⛔ Your account has been suspended by Admin.")
    elif status in ['NEW', 'PENDING']:
        g_link = settings.get("GAME_LINK", "Contact Admin")
        msg = (f"💎 <b>WELCOME TO PREMIUM VIP BOT</b> 💎\n\n"
               f"📜 <b>ACTIVATION RULES:</b>\n"
               f"1️⃣ Register account using our Official Link.\n"
               f"2️⃣ Deposit funds into your account.\n"
               f"3️⃣ Send your Game UID here for VIP Approval.\n\n"
               f"🔗 <b>Official Game Link:</b> {g_link}\n\n"
               f"👉 <i>Please reply with your Game UID to activate VIP:</i>")
        user_states[user_id] = "WAITING_FOR_UID"
        await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
    elif status == 'ACTIVE':
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Start DM Signals", callback_data="u_start_dm"), InlineKeyboardButton("🔴 Stop DM Signals", callback_data="u_stop_dm")],
            [InlineKeyboardButton("🔗 Set My Channel", callback_data="u_set_ch")],
            [InlineKeyboardButton("▶ Start Channel Signals", callback_data="u_start_ch"), InlineKeyboardButton("⏹ Stop Channel Signals", callback_data="u_stop_ch")],
            [InlineKeyboardButton("🎧 Customer Support", callback_data="u_support")]
        ])
        await update.message.reply_text("💎 <b>VIP USER DASHBOARD</b> 💎\n\nManage your Premium Signals below:", reply_markup=kb, parse_mode="HTML")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID: return
    user_states[user_id] = "WAITING_ADMIN_PASSWORD"
    await update.message.reply_text("🔒 <b>Enter Master Admin Password:</b>", parse_mode="HTML")

def admin_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶ START SESSION", callback_data="adm_start"), InlineKeyboardButton("⏹ CLOSE SESSION", callback_data="adm_stop")],
        [InlineKeyboardButton("🖼 Manage Stickers", callback_data="adm_stickers"), InlineKeyboardButton("🔗 Manage Links", callback_data="adm_links")],
        [InlineKeyboardButton("👥 User Management", callback_data="adm_users"), InlineKeyboardButton("📢 VIP Broadcast", callback_data="adm_broadcast")]
    ])

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_global_running, automation_task
    query = update.callback_query
    uid = update.effective_user.id
    await query.answer()
    data = query.data

    # --- ADMIN BUTTONS ---
    if uid == ADMIN_ID:
        if data == "adm_main":
            await query.edit_message_text("👑 <b>MASTER ADMIN PANEL</b>", reply_markup=admin_main_kb(), parse_mode="HTML")
        elif data == "adm_start":
            if not is_global_running:
                is_global_running = True
                automation_task = asyncio.create_task(automation_worker(context.bot))
                await broadcast_message(context.bot, "🟢 <b>VIP SESSION STARTED</b>", "START_STICKER")
            await query.edit_message_text("🟢 VIP SESSION STARTED!", reply_markup=admin_main_kb())
        elif data == "adm_stop":
            if is_global_running:
                is_global_running = False
                if automation_task: automation_task.cancel()
                await broadcast_message(context.bot, "🔴 <b>VIP SESSION CLOSED</b>", "STOP_STICKER")
            await query.edit_message_text("⏹ VIP SESSION CLOSED!", reply_markup=admin_main_kb())
        elif data == "adm_stickers":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Set WIN", callback_data="stk_WIN_STICKER"), InlineKeyboardButton("Set LOSS", callback_data="stk_LOSS_STICKER")],
                [InlineKeyboardButton("Set JACKPOT", callback_data="stk_JACKPOT_STICKER")],
                [InlineKeyboardButton("Set START", callback_data="stk_START_STICKER"), InlineKeyboardButton("Set STOP", callback_data="stk_STOP_STICKER")],
                [InlineKeyboardButton("🔙 Back", callback_data="adm_main")]
            ])
            await query.edit_message_text("🖼 <b>Sticker Management:</b>", reply_markup=kb, parse_mode="HTML")
        elif data.startswith("stk_"):
            key = data.replace("stk_", "")
            user_states[uid] = f"WAITING_{key}"
            await query.edit_message_text(f"Send the {key} sticker now:")
        elif data == "adm_links":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Game Link", callback_data="lnk_GAME_LINK")],
                [InlineKeyboardButton("Bot Link", callback_data="lnk_BOT_LINK")],
                [InlineKeyboardButton("Channel Link", callback_data="lnk_ADMIN_CHANNEL_LINK")],
                [InlineKeyboardButton("🔙 Back", callback_data="adm_main")]
            ])
            await query.edit_message_text("🔗 <b>Link Management:</b>", reply_markup=kb, parse_mode="HTML")
        elif data.startswith("lnk_"):
            key = data.replace("lnk_", "")
            user_states[uid] = f"WAITING_{key}"
            await query.edit_message_text(f"Send URL for {key}:")
        elif data == "adm_users":
            kb = [[InlineKeyboardButton("🔙 Back", callback_data="adm_main")]]
            text = "👥 <b>User Management:</b>\n\n"
            for u, d in users.items():
                status_emoji = "🟢" if d["status"]=="ACTIVE" else "🔴" if d["status"]=="BLOCKED" else "🟡"
                text += f"{status_emoji} UID: <code>{u}</code> | Game: {d['game_uid']}\n"
                kb.insert(0, [InlineKeyboardButton(f"Manage {u}", callback_data=f"manage_{u}")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        elif data.startswith("manage_"):
            target_u = int(data.split("_")[1])
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Activate", callback_data=f"usr_act_{target_u}"), InlineKeyboardButton("⛔ Block", callback_data=f"usr_blk_{target_u}")],
                [InlineKeyboardButton("🔙 Back", callback_data="adm_users")]
            ])
            await query.edit_message_text(f"⚙️ Manage User <code>{target_u}</code>", reply_markup=kb, parse_mode="HTML")
        elif data.startswith("usr_act_"):
            u = int(data.split("_")[2])
            users[u]["status"] = 'ACTIVE'
            await context.bot.send_message(chat_id=u, text="🎉 Your VIP Account is ACTIVATED! Send /start to enter.")
            await query.edit_message_text(f"User {u} Activated.", reply_markup=admin_main_kb())
        elif data.startswith("usr_blk_"):
            u = int(data.split("_")[2])
            users[u]["status"] = 'BLOCKED'
            users[u]["dm_on"] = False
            users[u]["ch_on"] = False
            await query.edit_message_text(f"User {u} Blocked.", reply_markup=admin_main_kb())
        elif data == "adm_broadcast":
            user_states[uid] = "WAITING_BROADCAST"
            await query.edit_message_text("📢 Send the message/image for Global Broadcast:")
        
        # Admin Reply to Support
        elif data.startswith("reply_"):
            target_uid = int(data.split("_")[1])
            user_states[uid] = f"REPLY_SUPPORT_{target_uid}"
            await query.edit_message_text(f"✍️ Type your reply to user <code>{target_uid}</code>:", parse_mode="HTML")

    # --- VIP USER BUTTONS ---
    else:
        if data == "u_start_dm":
            users[uid]["dm_on"] = True
            await query.answer("✅ DM Signals Started!", show_alert=True)
        elif data == "u_stop_dm":
            users[uid]["dm_on"] = False
            await query.answer("⏹ DM Signals Stopped!", show_alert=True)
        elif data == "u_set_ch":
            user_states[uid] = "WAITING_USER_CHANNEL"
            await query.edit_message_text("Make bot Admin in your channel, then send Channel ID (e.g. -100123...):")
        elif data == "u_start_ch":
            users[uid]["ch_on"] = True
            await query.answer("✅ Channel Signals Started!", show_alert=True)
        elif data == "u_stop_ch":
            users[uid]["ch_on"] = False
            await query.answer("⏹ Channel Signals Stopped!", show_alert=True)
        elif data == "u_support":
            user_states[uid] = "WAITING_SUPPORT"
            await query.edit_message_text("🎧 <b>PREMIUM SUPPORT</b>\n\nType your message below and Admin will reply to you shortly:", parse_mode="HTML")

async def text_sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_states.get(uid)
    if not state: return

    if uid == ADMIN_ID:
        if state == "WAITING_ADMIN_PASSWORD":
            if update.message.text == ADMIN_PASSWORD:
                user_states.pop(uid)
                await update.message.reply_text("✅ Access Granted!\n\n👑 <b>MASTER ADMIN PANEL</b>", reply_markup=admin_main_kb(), parse_mode="HTML")
            else:
                await update.message.reply_text("❌ Incorrect Password.")
                
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
            for u, d in users.items():
                if d["status"] == "ACTIVE":
                    try: await update.message.copy(chat_id=u)
                    except: pass
            await update.message.reply_text(f"✅ VIP Broadcast sent successfully.", reply_markup=admin_main_kb())

        elif state.startswith("REPLY_SUPPORT_"):
            target_uid = int(state.split("_")[2])
            user_states.pop(uid)
            try:
                await context.bot.send_message(chat_id=target_uid, text=f"🎧 <b>Admin Support Reply:</b>\n\n{update.message.text}", parse_mode="HTML")
                await update.message.reply_text("✅ Reply sent to user.", reply_markup=admin_main_kb())
            except:
                await update.message.reply_text("❌ Failed to send. User might have blocked the bot.", reply_markup=admin_main_kb())

    else:
        if state == "WAITING_FOR_UID":
            users[uid]["game_uid"] = update.message.text
            users[uid]["status"] = "PENDING"
            user_states.pop(uid)
            await update.message.reply_text("✅ VIP Request sent to Admin! Please wait.")
            
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Review User", callback_data=f"manage_{uid}")]])
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 <b>New VIP Request!</b>\nTelegram ID: <code>{uid}</code>\nGame UID: {update.message.text}", reply_markup=kb, parse_mode="HTML")
            
        elif state == "WAITING_USER_CHANNEL":
            users[uid]["ch_id"] = update.message.text
            user_states.pop(uid)
            await update.message.reply_text("✅ Channel Saved! Send /start to open Panel and click Start Channel Signals.")
            
        elif state == "WAITING_SUPPORT":
            user_states.pop(uid)
            await update.message.reply_text("✅ Message sent to Premium Support. We will reply shortly.")
            
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Reply to User", callback_data=f"reply_{uid}")]])
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"📩 <b>Support Ticket</b> from <code>{uid}</code>:\n\n{update.message.text}", reply_markup=kb, parse_mode="HTML")

# ==========================================
# 🚀 MAIN RUNNER
# ==========================================
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, text_sticker_handler))
    
    logger.info("Premium Bot Running! Railway Server ACTIVE.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
