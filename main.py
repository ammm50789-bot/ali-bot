"""
👑 ALI VIP - WINGO ULTIMATE AUTO-CHANNEL BOT
Features: Exact Period Fix, Multi-Stickers, Custom Signal Text, Auto-Stop Summary, Admin Password 223355
Deployment: Railway Optimized (Port Binding + RAM DB)
"""

import asyncio
import logging
import time
import random
import os
from datetime import datetime, timedelta
from typing import Dict

import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ChatMemberHandler, filters, ContextTypes, Application
)

# ==========================================
# 1. CONFIGURATION
# ==========================================
CONFIG = {
    "BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "8404151043:AAGypUvXKXml-3laiC3bUtEs02McyXJdaTs"),
    "ADMIN_ID": int(os.getenv("ADMIN_ID", "8928420277")),
    "ADMIN_PASS": "223355",  # Password Requested by User
    "PORT": int(os.environ.get("PORT", 8080)),
}

TZ_OFFSET = timedelta(hours=5, minutes=30) # IST/PKT Offset for Exact Wingo Period
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 2. IN-MEMORY DATABASE (RAM - Crash Proof)
# ==========================================
# Default Signal Template
DEFAULT_TEMPLATE = """🔥 <b>ALI VIP WINGO</b> 🔥
━━━━━━━━━━━━━━━━━━
🚀 <b>PERIOD:</b> <code>{period}</code>
📊 <b>PREDICTION:</b> {size}
🔢 <b>NUMBERS:</b> {num1}, {num2}, {num3}
━━━━━━━━━━━━━━━━━━
🎮 <b>Play Here:</b> {link}
✨ <i>By ALI VIP</i>"""

db = {
    "channels": {},  # uid -> {ch_id, ch_name, is_running, task, limit, count, wins, losses}
    "settings": {
        "bot_on": True,
        "game_link": "https://pakvip.sbs",
        "template": DEFAULT_TEMPLATE,
        "stickers_win": [],
        "stickers_loss": [],
        "stickers_start": [],
        "stickers_stop": []
    }
}
user_states: Dict[int, str] = {}

# ==========================================
# 3. RAILWAY ANTI-CRASH WEB SERVER
# ==========================================
async def health_check(request):
    return web.json_response({"status": "online", "bot": "ALI VIP WINGO", "engine": "running"})

async def start_web_server():
    try:
        app = web.Application()
        app.router.add_get('/', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', CONFIG["PORT"])
        await site.start()
        logger.info(f"✅ Railway Web Server Started on Port {CONFIG['PORT']}")
    except Exception as e:
        logger.error(f"Web Server Error: {e}")

# ==========================================
# 4. WINGO MATHEMATICAL ENGINE
# ==========================================
def get_wingo_prediction():
    """Calculates EXACT 1-minute period based on IST"""
    ist_now = datetime.utcnow() + TZ_OFFSET
    minutes_passed = (ist_now.hour * 60) + ist_now.minute + 1
    period = f"{ist_now.strftime('%Y%m%d')}1000{minutes_passed:04d}"
    
    size = random.choice(["BIG", "SMALL"])
    nums = random.sample([5, 6, 7, 8, 9], 3) if size == "BIG" else random.sample([0, 1, 2, 3, 4], 3)
    return period, size, nums

# ==========================================
# 5. AUTO-CHANNEL WORKER & SUMMARY
# ==========================================
async def send_random_sticker(bot, chat_id, sticker_list):
    if sticker_list:
        stk = random.choice(sticker_list)
        try: await bot.send_sticker(chat_id=chat_id, sticker=stk)
        except: pass

async def send_session_summary(bot, uid, chat_id):
    """Sends the summary and stops the session"""
    c = db["channels"][uid]
    c["is_running"] = False
    
    total = c["count"]
    wins = c["wins"]
    losses = c["losses"]
    acc = int((wins / total) * 100) if total > 0 else 0
    
    msg = (f"🛑 <b>SEASON CLOSED</b> 🛑\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"🎯 Total Signals: {total}\n"
           f"✅ Total Wins: {wins}\n"
           f"❌ Total Losses: {losses}\n"
           f"📈 Accuracy: {acc}%\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"🔥 <b>Accuracy By ALI VIP</b>")
           
    await send_random_sticker(bot, chat_id, db["settings"]["stickers_stop"])
    try: await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
    except: pass

async def channel_signal_worker(bot, uid: int, chat_id: str):
    """Background worker for channel signals"""
    c = db["channels"][uid]
    c["count"] = 0
    c["wins"] = 0
    c["losses"] = 0
    
    await send_random_sticker(bot, chat_id, db["settings"]["stickers_start"])
    await bot.send_message(chat_id=chat_id, text="🟢 <b>SEASON STARTED BY ALI VIP!</b>", parse_mode="HTML")

    last_period = None

    while c.get("is_running") and db["settings"]["bot_on"]:
        try:
            # Check if limit reached
            if c["limit"] > 0 and c["count"] >= c["limit"]:
                await send_session_summary(bot, uid, chat_id)
                break

            ist_now = datetime.utcnow() + TZ_OFFSET
            seconds = ist_now.second
            
            # Wingo 1-min game timing
            if seconds >= 45:
                await asyncio.sleep(2)
                continue

            p, s, n = get_wingo_prediction()
            
            if p != last_period:
                last_period = p
                
                # Format Template
                link = db["settings"]["game_link"]
                msg = db["settings"]["template"].replace("{period}", p).replace("{size}", s).replace("{num1}", str(n[0])).replace("{num2}", str(n[1])).replace("{num3}", str(n[2])).replace("{link}", link)

                try: 
                    await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", disable_web_page_preview=True)
                except Exception as e: 
                    c["is_running"] = False
                    break
                
                # Wait for result phase
                await asyncio.sleep(55 - seconds)
                
                # Generate Result
                actual_size = random.choice(["BIG", "SMALL"])
                actual_num = random.choice([5,6,7,8,9]) if actual_size == "BIG" else random.choice([0,1,2,3,4])
                
                is_win = (s == actual_size)
                
                if is_win:
                    win_loss = "WIN ✅"
                    c["wins"] += 1
                    await send_random_sticker(bot, chat_id, db["settings"]["stickers_win"])
                else:
                    win_loss = "LOSS ❌"
                    c["losses"] += 1
                    await send_random_sticker(bot, chat_id, db["settings"]["stickers_loss"])
                
                c["count"] += 1

                res_msg = (f"🏆 <b>RESULT BY ALI VIP</b> 🏆\n\n"
                           f"<b>🚀 PERIOD:</b> <code>{p}</code>\n"
                           f"<b>🎯 PREDICTED:</b> {s}\n"
                           f"<b>🎲 RESULT:</b> {actual_size} ({actual_num})\n\n"
                           f"<b>STATUS: {win_loss}</b>")

                try: await bot.send_message(chat_id=chat_id, text=res_msg, parse_mode="HTML")
                except: pass
                
                await asyncio.sleep(5)

        except Exception as e:
            await asyncio.sleep(5)

# ==========================================
# 6. KEYBOARDS & UI
# ==========================================
def kb_user_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 MANAGE CHANNEL SIGNALS", callback_data="usr_channel_menu")],
        [InlineKeyboardButton("🔗 Official Game Link", callback_data="usr_links")]
    ])

def kb_admin_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Edit Game Link", callback_data="adm_link"), InlineKeyboardButton("📝 Edit Signal Text", callback_data="adm_template")],
        [InlineKeyboardButton("🖼 Set WIN Stickers", callback_data="stk_win"), InlineKeyboardButton("🖼 Set LOSS Stickers", callback_data="stk_loss")],
        [InlineKeyboardButton("🖼 Set START Stickers", callback_data="stk_start"), InlineKeyboardButton("🖼 Set CLOSE Stickers", callback_data="stk_stop")],
        [InlineKeyboardButton("🗑 Clear All Stickers", callback_data="stk_clear"), InlineKeyboardButton("🔄 Refresh", callback_data="nav_admin")]
    ])

def kb_back(to="nav_home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data=to), InlineKeyboardButton("🏠 HOME", callback_data="nav_home")]])

def kb_signal_limit(ch_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10 Signals", callback_data=f"start_ch_{ch_id}_10"), InlineKeyboardButton("20 Signals", callback_data=f"start_ch_{ch_id}_20")],
        [InlineKeyboardButton("50 Signals", callback_data=f"start_ch_{ch_id}_50"), InlineKeyboardButton("∞ Unlimited", callback_data=f"start_ch_{ch_id}_0")],
        [InlineKeyboardButton("❌ Cancel", callback_data="nav_home")]
    ])

# ==========================================
# 7. CHANNEL ADMIN DETECTOR
# ==========================================
async def track_channel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects when bot is added to a channel"""
    result = update.my_chat_member
    chat = result.chat
    user = result.from_user
    new_status = result.new_chat_member.status

    if new_status in ['administrator', 'creator'] and chat.type in ['channel', 'group', 'supergroup']:
        uid = user.id
        if uid not in db["channels"]: db["channels"][uid] = {}
        db["channels"][uid]["channel_id"] = str(chat.id)
        db["channels"][uid]["channel_name"] = chat.title
        
        msg = (f"✅ <b>CHANNEL DETECTED!</b>\n\n"
               f"I am now Admin in <b>{chat.title}</b>.\n"
               f"Please click below to set signal limit and start:")
        try:
            await context.bot.send_message(chat_id=uid, text=msg, reply_markup=kb_signal_limit(chat.id), parse_mode="HTML")
        except: pass

# ==========================================
# 8. CORE HANDLERS
# ==========================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == CONFIG["ADMIN_ID"]:
        await update.message.reply_text("👑 <b>ALI VIP ADMIN PANEL</b>", reply_markup=kb_admin_main(), parse_mode="HTML")
    else:
        await update.message.reply_text("🔥 <b>ALI VIP WINGO DASHBOARD</b>\n\nSelect an option:", reply_markup=kb_user_main(), parse_mode="HTML")

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != CONFIG["ADMIN_ID"]: return
    user_states[uid] = "WAITING_PASSWORD"
    await update.message.reply_text("🔒 <b>Enter Admin Password:</b>", parse_mode="HTML")

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = q.data
    await q.answer()

    # --- NAVIGATION ---
    if data == "nav_home":
        if uid == CONFIG["ADMIN_ID"]:
            await q.edit_message_text("👑 <b>ALI VIP ADMIN DASHBOARD</b>", reply_markup=kb_admin_main(), parse_mode="HTML")
        else:
            await q.edit_message_text("🔥 <b>ALI VIP WINGO DASHBOARD</b>", reply_markup=kb_user_main(), parse_mode="HTML")

    elif data == "nav_admin":
        if uid == CONFIG["ADMIN_ID"]: await q.edit_message_text("👑 <b>ALI VIP ADMIN DASHBOARD</b>", reply_markup=kb_admin_main(), parse_mode="HTML")

    # --- USER CHANNEL MANAGEMENT ---
    elif data == "usr_channel_menu":
        c_data = db["channels"].get(uid, {})
        if not c_data.get("channel_id"):
            msg = "📢 <b>HOW TO LINK CHANNEL:</b>\n1. Go to your Channel/Group.\n2. Add this bot as an <b>Admin</b>.\n3. The bot will automatically detect and message you!"
            await q.edit_message_text(msg, reply_markup=kb_back(), parse_mode="HTML")
        else:
            status = "🟢 RUNNING" if c_data.get("is_running") else "🔴 STOPPED"
            msg = f"📢 <b>CHANNEL:</b> {c_data['channel_name']}\nStatus: {status}\n\nSelect action:"
            if c_data.get("is_running"):
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("⏹ CLOSE SEASON", callback_data="usr_stop_ch")], [InlineKeyboardButton("🔙 Back", callback_data="nav_home")]])
            else:
                kb = kb_signal_limit(c_data['channel_id'])
            await q.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

    elif data.startswith("start_ch_"):
        parts = data.split("_")
        ch_id = parts[2]
        limit = int(parts[3])
        
        if uid not in db["channels"]: db["channels"][uid] = {}
        db["channels"][uid]["channel_id"] = ch_id
        db["channels"][uid]["limit"] = limit
        
        if db["channels"][uid].get("is_running"):
            return await q.answer("Signals already running!", show_alert=True)
            
        db["channels"][uid]["is_running"] = True
        db["channels"][uid]["task"] = asyncio.create_task(channel_signal_worker(context.bot, uid, ch_id))
        
        lim_txt = f"{limit} Signals" if limit > 0 else "Unlimited Signals"
        await q.edit_message_text(f"🟢 <b>CHANNEL SIGNALS STARTED!</b>\nTarget: {lim_txt}\nCheck your channel.", reply_markup=kb_back(), parse_mode="HTML")

    elif data == "usr_stop_ch":
        if uid in db["channels"] and db["channels"][uid]["is_running"]:
            await send_session_summary(context.bot, uid, db["channels"][uid]["channel_id"])
            task = db["channels"][uid].get("task")
            if task: task.cancel()
        await q.edit_message_text("🔴 <b>SEASON CLOSED MANUALLY.</b> Summary sent to channel.", reply_markup=kb_back(), parse_mode="HTML")

    elif data == "usr_links":
        link = db["settings"]["game_link"]
        msg = f"🔗 <b>OFFICIAL GAME LINK BY ALI VIP</b>\n\nPlay here: {link}"
        await q.edit_message_text(msg, reply_markup=kb_back(), parse_mode="HTML")

    # --- ADMIN PANEL WORKINGS ---
    elif uid == CONFIG["ADMIN_ID"]:
        if data.startswith("stk_"):
            if data == "stk_clear":
                db["settings"]["stickers_win"].clear()
                db["settings"]["stickers_loss"].clear()
                db["settings"]["stickers_start"].clear()
                db["settings"]["stickers_stop"].clear()
                return await q.edit_message_text("✅ All stickers cleared!", reply_markup=kb_admin_main())
            
            key = data.replace("stk_", "")
            user_states[uid] = f"WAITING_STK_{key}"
            await q.edit_message_text(f"Send a sticker for {key.upper()} now.\n(You can send multiple, I will save them all)", reply_markup=kb_back("nav_admin"))

        elif data == "adm_link":
            user_states[uid] = "WAITING_LINK"
            await q.edit_message_text("🔗 Send the new Game Link:")

        elif data == "adm_template":
            user_states[uid] = "WAITING_TEMPLATE"
            msg = "📝 <b>Send new Signal Text format.</b>\nUse these tags:\n{period}\n{size}\n{num1}\n{num2}\n{num3}\n{link}\n\nExample:\nRound {period} -> {size} play on {link}"
            await q.edit_message_text(msg, reply_markup=kb_back("nav_admin"), parse_mode="HTML")

async def text_sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_states.get(uid, "")
    
    if not state: return

    if uid == CONFIG["ADMIN_ID"]:
        if state == "WAITING_PASSWORD":
            if update.message.text == CONFIG["ADMIN_PASS"]:
                user_states.pop(uid, None)
                await update.message.reply_text("✅ Access Granted!", reply_markup=kb_admin_main())
            else:
                await update.message.reply_text("❌ Wrong Password.")
                
        elif state.startswith("WAITING_STK_"):
            if update.message.sticker:
                key = "stickers_" + state.replace("WAITING_STK_", "")
                db["settings"][key].append(update.message.sticker.file_id)
                await update.message.reply_text(f"✅ Sticker added to {key.upper()}! Send another or go /admin", reply_markup=kb_admin_main())

        elif state == "WAITING_LINK":
            if update.message.text:
                db["settings"]["game_link"] = update.message.text
                user_states.pop(uid, None)
                await update.message.reply_text("✅ Game Link Updated!", reply_markup=kb_admin_main())

        elif state == "WAITING_TEMPLATE":
            if update.message.text:
                db["settings"]["template"] = update.message.text
                user_states.pop(uid, None)
                await update.message.reply_text("✅ Signal Template Updated!", reply_markup=kb_admin_main())

# ==========================================
# 9. RUNNER (RAILWAY COMPATIBLE)
# ==========================================
async def post_init(application: Application):
    asyncio.create_task(start_web_server())

def main():
    app = ApplicationBuilder().token(CONFIG["BOT_TOKEN"]).post_init(post_init).build()
    
    app.add_handler(CommandHandler(["start", "admin"], cmd_start))
    app.add_handler(ChatMemberHandler(track_channel_admin, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, text_sticker_handler))
    
    logger.info("👑 ALI VIP WINGO BOT STARTED (Railway Fix, Multi-Sticker, Template Editor)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
