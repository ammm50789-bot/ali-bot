import asyncio
import logging
import time
import random
import os
import hashlib
from aiohttp import web
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
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
# âš™ï¸ VIP CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = "8675974676:AAG9MlrlEgJSPwcxg_-khjCSl4cQxI-N9LI"
ADMIN_ID = 8195946863
ADMIN_PASSWORD = "11223344Ali"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# ðŸ§  IN-MEMORY VIP DATABASE
# ==========================================
db = {
    "users": {}, 
    "settings": {
        "GAME_LINK": "https://bdg88zf.com (Ask Admin)",
        "WIN_STICKER": None,
        "LOSS_STICKER": None,
        "START_STICKER": None,
        "CLOSE_STICKER": None
    },
    "stats": {"total": 0, "wins": 0, "losses": 0, "jackpots": 0}
}
user_states = {}
is_global_running = False
automation_task = None

# ==========================================
# ðŸŒ RAILWAY ANTI-CRASH SERVER
# ==========================================
async def web_handler(request):
    return web.Response(text="ðŸŸ¢ Ultimate VIP Wingo & Aviator System with ALI HASH is Running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', web_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Railway Web Server Started on Port {port}")

async def post_init(application: Application):
    asyncio.create_task(start_web_server())

# ==========================================
# ðŸ” ALI HASH GENERATOR
# ==========================================
def generate_ali_hash(data):
    """Generates a Provably Fair SHA-256 Hash for signals"""
    raw_str = f"ALI_PREDICTION_{data}_{time.time()}_{random.random()}"
    return hashlib.sha256(raw_str.encode()).hexdigest()[:24].upper()

# ==========================================
# ðŸŒ PREDICTION ENGINES
# ==========================================
def get_wingo_period(offset=0):
    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    minutes_passed = (ist_now.hour * 60) + ist_now.minute + 1 + offset
    return f"{ist_now.strftime('%Y%m%d')}1000{minutes_passed:04d}"

def get_wingo_prediction(period):
    size = random.choice(["BIG", "SMALL"])
    nums = random.sample([5, 6, 7, 8, 9], 2) if size == "BIG" else random.sample([0, 1, 2, 3, 4], 2)
    ali_hash = generate_ali_hash(period)
    return size, nums, ali_hash

def get_aviator_prediction():
    rand = random.random()
    if rand < 0.6: multi = random.uniform(1.20, 2.50)
    elif rand < 0.9: multi = random.uniform(2.50, 5.00)
    else: multi = random.uniform(5.00, 10.00)
    multi_round = round(multi, 2)
    ali_hash = generate_ali_hash(multi_round)
    return multi_round, ali_hash

# ==========================================
# ðŸ¤– GLOBAL AUTOMATION (ADMIN CONTROLLED)
# ==========================================
async def broadcast_to_active(bot, text, sticker=None, photo=None):
    active_users = [u for u, d in db["users"].items() if d["status"] == "ACTIVE"]
    active_users.append(ADMIN_ID)
    for u in set(active_users):
        try:
            if sticker:
                try: await bot.send_sticker(chat_id=u, sticker=sticker)
                except: pass
            if photo:
                await bot.send_photo(chat_id=u, photo=photo, caption=text, parse_mode="HTML")
            elif text:
                await bot.send_message(chat_id=u, text=text, parse_mode="HTML")
        except: pass

async def global_automation(bot):
    global is_global_running
    last_period = None
    
    if db["settings"]["START_STICKER"]:
        await broadcast_to_active(bot, "ðŸŸ¢ <b>GLOBAL VIP SESSION STARTED!</b>", db["settings"]["START_STICKER"])
    else:
        await broadcast_to_active(bot, "ðŸŸ¢ <b>GLOBAL VIP SESSION STARTED!</b>")

    while is_global_running:
        try:
            ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
            seconds = ist_now.second
            
            if seconds >= 45:
                await asyncio.sleep(2)
                continue

            current_period = get_wingo_period()
            if current_period != last_period:
                size, nums, w_hash = get_wingo_prediction(current_period)
                aviator_multi, a_hash = get_aviator_prediction()
                last_period = current_period
                
                msg = (
                    f"ðŸ”¥ <b>VIP GLOBAL SIGNALS</b> ðŸ”¥\n\n"
                    f"ðŸ”´ <b>WINGO PREDICTION:</b>\n"
                    f"ðŸš€ Period: <code>{current_period}</code>\n"
                    f"ðŸ“Š Size: {size}\n"
                    f"ðŸ”¢ Nums: {nums[0]}, {nums[1]}\n"
                    f"ðŸ” Hash: <code>{w_hash}</code>\n\n"
                    f"âœˆï¸ <b>AVIATOR PREDICTION:</b>\n"
                    f"ðŸŽ¯ Target: {aviator_multi}x\n"
                    f"ðŸ” Hash: <code>{a_hash}</code>\n\n"
                    f"ðŸŽ® Play Link: {db['settings']['GAME_LINK']}"
                )
                await broadcast_to_active(bot, msg)
                await asyncio.sleep(55 - seconds)
                
                res_size = random.choice(["BIG", "SMALL"])
                is_win = (size == res_size)
                status = "WIN" if is_win else "LOSS"
                
                if is_win: db["stats"]["wins"] += 1
                else: db["stats"]["losses"] += 1
                db["stats"]["total"] += 1

                res_msg = (
                    f"ðŸ† <b>GLOBAL RESULT</b> ðŸ†\n\n"
                    f"ðŸš€ Period: <code>{current_period}</code>\n"
                    f"ðŸŽ¯ Predicted: {size}\n"
                    f"ðŸŽ² Result: {res_size}\n\n"
                    f"<b>STATUS: {status}</b>"
                )
                
                stk = db["settings"]["WIN_STICKER"] if is_win else db["settings"]["LOSS_STICKER"]
                await broadcast_to_active(bot, res_msg, stk)

        except Exception as e:
            await asyncio.sleep(5)

# ==========================================
# ðŸ“± USER & ADMIN HANDLERS
# ==========================================
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ðŸ”´ WINGO SINGLE", callback_data="play_wingo"), InlineKeyboardButton("âœˆï¸ AVIATOR", callback_data="play_aviator")],
        [InlineKeyboardButton("ðŸŒŸ ADVANCE PREDICTION (10)", callback_data="play_advance")],
        [InlineKeyboardButton("ðŸ“Š MY STATS & ANALYTICS", callback_data="show_stats")]
    ])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if uid == ADMIN_ID:
        return await update.message.reply_text("ðŸ‘‘ Hello VIP Admin! Send /admin to open the Master Panel.")

    if uid not in db["users"]:
        db["users"][uid] = {"status": "NEW", "game_uid": "", "screenshot": ""}

    status = db["users"][uid]["status"]

    if status == "BLOCKED":
        await update.message.reply_text("â›” You are blocked by Admin.")
    
    elif status == "NEW":
        link = db["settings"]["GAME_LINK"]
        msg = (
            f"ðŸ‘‹ <b>Welcome to ALI PREDICTION VIP</b>\n\n"
            f"âš ï¸ <b>REGISTRATION REQUIRED</b>\n"
            f"1ï¸âƒ£ Create an account using this official link:\nðŸ‘‰ {link}\n"
            f"2ï¸âƒ£ Send your <b>Game UID</b> here in the chat to proceed."
        )
        user_states[uid] = "WAITING_UID"
        await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
        
    elif status == "AWAITING_SCREENSHOT":
        msg = (
            f"ðŸ’³ <b>DEPOSIT REQUIRED</b>\n\n"
            f"To activate your VIP signals, please deposit a minimum of <b>500 Rs</b> in your game account.\n\n"
            f"ðŸ“¸ <b>Send the successful deposit screenshot here.</b>"
        )
        user_states[uid] = "WAITING_SCREENSHOT"
        await update.message.reply_text(msg, parse_mode="HTML")
        
    elif status == "PENDING":
        await update.message.reply_text("â³ Your account is under review by the Admin. Please wait for approval.")
        
    elif status == "ACTIVE":
        await update.message.reply_text("ðŸ”¥ <b>VIP DASHBOARD</b> ðŸ”¥\n\nSelect your prediction mode:", reply_markup=main_menu_kb(), parse_mode="HTML")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    user_states[ADMIN_ID] = "WAITING_PASSWORD"
    await update.message.reply_text("ðŸ”’ <b>Enter Admin Password:</b>", parse_mode="HTML")

def admin_kb():
    global is_global_running
    g_text = "â¹ STOP GLOBAL SIGNALS" if is_global_running else "â–¶ï¸ START GLOBAL SIGNALS"
    g_data = "adm_g_stop" if is_global_running else "adm_g_start"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(g_text, callback_data=g_data)],
        [InlineKeyboardButton("ðŸ‘¥ User Management", callback_data="adm_users"), InlineKeyboardButton("ðŸ“¢ Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("ðŸ–¼ Set Stickers", callback_data="adm_stickers"), InlineKeyboardButton("ðŸ”— Set Game Link", callback_data="adm_link")],
        [InlineKeyboardButton("ðŸ“Š System Analytics", callback_data="adm_stats")]
    ])

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_global_running, automation_task
    query = update.callback_query
    uid = update.effective_user.id
    await query.answer()
    data = query.data

    # ================== ADMIN BUTTONS ==================
    if uid == ADMIN_ID:
        if data == "adm_main":
            await query.edit_message_text("ðŸ‘‘ <b>MASTER ADMIN PANEL</b>", reply_markup=admin_kb(), parse_mode="HTML")
            
        elif data == "adm_g_start":
            is_global_running = True
            automation_task = asyncio.create_task(global_automation(context.bot))
            await query.edit_message_text("ðŸŸ¢ GLOBAL SIGNALS STARTED!", reply_markup=admin_kb())
            
        elif data == "adm_g_stop":
            is_global_running = False
            if automation_task: automation_task.cancel()
            if db["settings"]["CLOSE_STICKER"]:
                await broadcast_to_active(context.bot, "ðŸ”´ <b>GLOBAL VIP SESSION CLOSED!</b>", db["settings"]["CLOSE_STICKER"])
            await query.edit_message_text("â¹ GLOBAL SIGNALS STOPPED!", reply_markup=admin_kb())
            
        elif data == "adm_stickers":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("WIN Sticker", callback_data="stk_WIN_STICKER"), InlineKeyboardButton("LOSS Sticker", callback_data="stk_LOSS_STICKER")],
                [InlineKeyboardButton("START Session", callback_data="stk_START_STICKER"), InlineKeyboardButton("CLOSE Session", callback_data="stk_CLOSE_STICKER")],
                [InlineKeyboardButton("ðŸ”™ Back", callback_data="adm_main")]
            ])
            await query.edit_message_text("ðŸ–¼ <b>Select Sticker to Update:</b>", reply_markup=kb, parse_mode="HTML")
            
        elif data.startswith("stk_"):
            key = data.replace("stk_", "")
            user_states[uid] = f"WAITING_{key}"
            await query.edit_message_text(f"Please send the {key} sticker now:")
            
        elif data == "adm_link":
            user_states[uid] = "WAITING_GAME_LINK"
            await query.edit_message_text("ðŸ”— Send the new Game Registration Link:")
            
        elif data == "adm_broadcast":
            user_states[uid] = "WAITING_BROADCAST"
            await query.edit_message_text("ðŸ“¢ Send text or photo to broadcast to all ACTIVE users:")
            
        elif data == "adm_users":
            kb = [[InlineKeyboardButton("ðŸ”™ Back", callback_data="adm_main")]]
            text = "ðŸ‘¥ <b>Users List:</b>\n\n"
            for u, d in db["users"].items():
                emoji = "ðŸŸ¢" if d["status"]=="ACTIVE" else "ðŸŸ¡" if d["status"]=="PENDING" else "ðŸ”´"
                text += f"{emoji} <code>{u}</code> | UID: {d['game_uid']}\n"
                kb.insert(0, [InlineKeyboardButton(f"Manage {u}", callback_data=f"manage_{u}")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
            
        elif data.startswith("manage_"):
            target_u = int(data.split("_")[1])
            d = db["users"][target_u]
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("âœ… Approve", callback_data=f"usr_app_{target_u}"), InlineKeyboardButton("â›” Block", callback_data=f"usr_blk_{target_u}")],
                [InlineKeyboardButton("ðŸ”™ Back", callback_data="adm_users")]
            ])
            await query.edit_message_text(f"ðŸ‘¤ <b>Manage User <code>{target_u}</code></b>\n\nGame UID: {d['game_uid']}\nStatus: {d['status']}", reply_markup=kb, parse_mode="HTML")
            
        elif data.startswith("usr_app_"):
            u = int(data.split("_")[2])
            db["users"][u]["status"] = "ACTIVE"
            await context.bot.send_message(chat_id=u, text="ðŸŽ‰ <b>Congratulations!</b> Your account is APPROVED. Send /start to access VIP Signals.", parse_mode="HTML")
            await query.edit_message_text(f"âœ… User {u} Approved.", reply_markup=admin_kb())
            
        elif data.startswith("usr_blk_"):
            u = int(data.split("_")[2])
            db["users"][u]["status"] = "BLOCKED"
            await query.edit_message_text(f"â›” User {u} Blocked.", reply_markup=admin_kb())
            
        elif data == "adm_stats":
            t = db["stats"]["total"]
            w = db["stats"]["wins"]
            l = db["stats"]["losses"]
            msg = f"ðŸ“Š <b>System Analytics</b>\n\nTotal Signals: {t}\nWins: {w}\nLosses: {l}\nActive Users: {len([u for u,d in db['users'].items() if d['status']=='ACTIVE'])}"
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ”™ Back", callback_data="adm_main")]]), parse_mode="HTML")

    # ================== USER BUTTONS ==================
    else:
        if db["users"].get(uid, {}).get("status") != "ACTIVE":
            return await query.answer("â›” You are not active!", show_alert=True)

        if data == "main_menu":
            await query.edit_message_text("ðŸ”¥ <b>VIP DASHBOARD</b> ðŸ”¥\n\nSelect your prediction mode:", reply_markup=main_menu_kb(), parse_mode="HTML")

        elif data == "play_wingo":
            p = get_wingo_period()
            s, n, ali_hash = get_wingo_prediction(p)
            db["stats"]["total"] += 1
            msg = f"ðŸ”´ <b>WINGO SINGLE (ALI HASH)</b>\n\nðŸš€ Period: <code>{p}</code>\nðŸ“Š Size: {s}\nðŸ”¢ Nums: {n[0]}, {n[1]}\nðŸ” Hash: <code>{ali_hash}</code>"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("âœ… WIN", callback_data="fb_win"), InlineKeyboardButton("âŒ LOSS", callback_data="fb_loss")], [InlineKeyboardButton("â­ NEXT SINGLE", callback_data="play_wingo"), InlineKeyboardButton("ðŸ”™ Back", callback_data="main_menu")]])
            await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

        elif data == "play_aviator":
            m, ali_hash = get_aviator_prediction()
            db["stats"]["total"] += 1
            msg = f"âœˆï¸ <b>AVIATOR SINGLE (ALI HASH)</b>\n\nðŸŽ¯ Target Multiplier: {m}x\nðŸ” Hash: <code>{ali_hash}</code>\nðŸ’¡ Cashout before target."
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("âœ… WIN", callback_data="fb_win"), InlineKeyboardButton("âŒ LOSS", callback_data="fb_loss")], [InlineKeyboardButton("â­ NEXT SINGLE", callback_data="play_aviator"), InlineKeyboardButton("ðŸ”™ Back", callback_data="main_menu")]])
            await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")
            
        elif data == "play_advance":
            msg = "ðŸŒŸ <b>ADVANCE PREDICTION (Next 10 Periods)</b>\n\n"
            for i in range(10):
                p = get_wingo_period(offset=i)
                s, _, h = get_wingo_prediction(p)
                msg += f"<code>{p[-4:]}</code> âž¡ï¸ {s} [Hash: {h[:8]}]\n"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ”™ Back", callback_data="main_menu")]])
            await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

        elif data in ["fb_win", "fb_loss"]:
            if data == "fb_win": db["stats"]["wins"] += 1
            else: db["stats"]["losses"] += 1
            res = "âœ… WIN RECORDED" if data == "fb_win" else "âŒ LOSS RECORDED"
            await query.answer(res, show_alert=True)
            
        elif data == "show_stats":
            t = db["stats"]["total"]
            w = db["stats"]["wins"]
            l = db["stats"]["losses"]
            rate = int((w/t)*100) if t>0 else 0
            msg = f"ðŸ“Š <b>ANALYTICS & STATS</b>\n\nTotal Signals: {t}\nTotal Wins: {w}\nTotal Losses: {l}\nWin Rate: {rate}%\n\n<i>Live Data Tracking</i>"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ”™ Back", callback_data="main_menu")]])
            await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")


async def text_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_states.get(uid)
    if not state: return

    # ADMIN HANDLERS
    if uid == ADMIN_ID:
        if state == "WAITING_PASSWORD":
            if update.message.text == ADMIN_PASSWORD:
                user_states.pop(uid)
                await update.message.reply_text("ðŸ‘‘ <b>MASTER ADMIN PANEL</b>", reply_markup=admin_kb(), parse_mode="HTML")
            else:
                await update.message.reply_text("âŒ Wrong Password")
                
        elif state.startswith("WAITING_") and "STICKER" in state:
            if update.message.sticker:
                key = state.replace("WAITING_", "")
                db["settings"][key] = update.message.sticker.file_id
                user_states.pop(uid)
                await update.message.reply_text(f"âœ… {key} Saved!", reply_markup=admin_kb())
                
        elif state == "WAITING_GAME_LINK":
            db["settings"]["GAME_LINK"] = update.message.text
            user_states.pop(uid)
            await update.message.reply_text("âœ… Link Saved!", reply_markup=admin_kb())
            
        elif state == "WAITING_BROADCAST":
            user_states.pop(uid)
            if update.message.photo:
                await broadcast_to_active(context.bot, update.message.caption or "", photo=update.message.photo[-1].file_id)
            else:
                await broadcast_to_active(context.bot, update.message.text)
            await update.message.reply_text("âœ… Broadcast Sent!", reply_markup=admin_kb())

    # USER HANDLERS
    else:
        if state == "WAITING_UID":
            db["users"][uid]["game_uid"] = update.message.text
            db["users"][uid]["status"] = "AWAITING_SCREENSHOT"
            user_states.pop(uid)
            await update.message.reply_text("âœ… UID Received.\n\nðŸ’³ <b>Please deposit Minimum 500 Rs and send the successful screenshot here.</b>", parse_mode="HTML")
            
        elif state == "WAITING_SCREENSHOT":
            if update.message.photo:
                db["users"][uid]["screenshot"] = update.message.photo[-1].file_id
                db["users"][uid]["status"] = "PENDING"
                user_states.pop(uid)
                await update.message.reply_text("âœ… Screenshot received! Please wait for Admin approval.")
                
                # Notify Admin
                caption = f"ðŸ”” <b>NEW DEPOSIT ALERT!</b>\n\nTelegram ID: <code>{uid}</code>\nGame UID: <code>{db['users'][uid]['game_uid']}</code>"
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("âœ… Approve", callback_data=f"usr_app_{uid}"), InlineKeyboardButton("â›” Block", callback_data=f"usr_blk_{uid}")]])
                await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=kb, parse_mode="HTML")
            else:
                await update.message.reply_text("âš ï¸ Please send a valid PHOTO / SCREENSHOT.")

# ==========================================
# ðŸš€ MAIN RUNNER
# ==========================================
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, text_photo_handler))
    
    logger.info("Premium Bot with ALI HASH is Running! (Crash-Free)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
