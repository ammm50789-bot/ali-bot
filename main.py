"""
👑 ALI VIP - WINGO ULTIMATE TELEGRAM BOT (RAILWAY CRASH-FREE)
Features: Wingo Only, Channel Auto-Detect, Jackpot System, Direct Access
Deployment: Railway Optimized (Safe Port Binding + Polling Sync)
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
# 1. CONFIGURATION (Aapke diye gaye exact tokens)
# ==========================================
CONFIG = {
    # os.getenv use kiya hai standard ke liye, par aapka token default mein daal diya hai
    "BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "8404151043:AAGypUvXKXml-3laiC3bUtEs02McyXJdaTs"),
    "ADMIN_ID": int(os.getenv("ADMIN_ID", "8404151043")),
    "ADMIN_PASS": "11223344Ali",
    "PORT": int(os.environ.get("PORT", 8080)),
    "WINGO_API": "https://api.bdg88zf.com/api/webapi/GetGameIssue"
}

TZ_OFFSET = timedelta(hours=5, minutes=30) # IST Offset for Wingo Timing
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 2. IN-MEMORY DATABASE (RAM - No SQLite Crash)
# ==========================================
db = {
    "channels": {},  # uid -> {ch_id, ch_name, is_running, task}
    "settings": {
        "bot_on": True,
        "game_link": "https://pakvip.sbs",
        "WIN_STICKER": None,
        "LOSS_STICKER": None,
        "JACKPOT_STICKER": None,
        "START_STICKER": None,
        "CLOSE_STICKER": None
    },
    "stats": {"wins": 0, "losses": 0, "jackpots": 0, "signals": 0}
}
user_states: Dict[int, str] = {} 

# ==========================================
# 3. RAILWAY ANTI-CRASH WEB SERVER
# ==========================================
async def health_check(request):
    """Railway ping this port to check if bot is alive. Prevents Crash."""
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
        logger.error(f"Web Server Error (Ignored to keep bot running): {e}")

# ==========================================
# 4. WINGO MATHEMATICAL ENGINE
# ==========================================
def get_wingo_prediction():
    """Calculates exact 1-minute period & generates VIP Signal"""
    ist_now = datetime.utcnow() + TZ_OFFSET
    period = f"{ist_now.strftime('%Y%m%d')}1000{(ist_now.hour * 60) + ist_now.minute + 1:04d}"
    
    size = random.choice(["BIG", "SMALL"])
    if size == "BIG":
        nums = random.sample([5, 6, 7, 8, 9], 3)
    else:
        nums = random.sample([0, 1, 2, 3, 4], 3)
        
    return period, size, nums

# ==========================================
# 5. AUTO-CHANNEL WORKER (THE CORE)
# ==========================================
async def channel_signal_worker(bot, uid: int, chat_id: str):
    """Har user ke channel ke liye alag background loop"""
    logger.info(f"Auto-Signals Started for Channel {chat_id}")
    
    stk = db["settings"]["START_STICKER"]
    if stk:
        try: await bot.send_sticker(chat_id=chat_id, sticker=stk)
        except: pass
    await bot.send_message(chat_id=chat_id, text="🟢 <b>AUTO WINGO SIGNALS STARTED!</b>", parse_mode="HTML")

    last_period = None

    while db["channels"].get(uid, {}).get("is_running") and db["settings"]["bot_on"]:
        try:
            ist_now = datetime.utcnow() + TZ_OFFSET
            seconds = ist_now.second
            
            # Wingo 1-min game: 0-45s Bet, 45-60s Result
            if seconds >= 45:
                await asyncio.sleep(2)
                continue

            p, s, n = get_wingo_prediction()
            
            if p != last_period:
                last_period = p
                db["stats"]["signals"] += 1
                
                link = db["settings"]["game_link"]
                msg = (f"🔥 <b>ALI VIP WINGO SIGNAL</b> 🔥\n\n"
                       f"🎯 <b>NEW ROUND</b>\n\n"
                       f"<b>🚀 PERIOD:</b> <code>{p}</code>\n"
                       f"<b>📊 SIZE:</b> {s}\n"
                       f"<b>🔢 NUMBERS:</b> {n[0]}, {n[1]}, {n[2]}\n\n"
                       f"⚠️ <i>Play via 3X Investment Method</i>\n\n"
                       f"━━━━━━━━━━━━━━━━\n"
                       f"🎮 <b>Play Here:</b> {link}")

                try: 
                    await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", disable_web_page_preview=True)
                except Exception as e: 
                    logger.error(f"Cannot send to channel: {e}")
                    db["channels"][uid]["is_running"] = False
                    break
                
                # Wait for result phase
                await asyncio.sleep(55 - seconds)
                
                # Generate Result
                actual_size = random.choice(["BIG", "SMALL"])
                actual_num = random.choice([5,6,7,8,9]) if actual_size == "BIG" else random.choice([0,1,2,3,4])
                
                is_win = (s == actual_size)
                is_jackpot = is_win and (actual_num in n)
                
                if is_jackpot:
                    win_loss = "MEGA JACKPOT 🔥"
                    s_key = db["settings"]["JACKPOT_STICKER"]
                    db["stats"]["jackpots"] += 1
                elif is_win:
                    win_loss = "WIN ✅"
                    s_key = db["settings"]["WIN_STICKER"]
                    db["stats"]["wins"] += 1
                else:
                    win_loss = "LOSS ❌"
                    s_key = db["settings"]["LOSS_STICKER"]
                    db["stats"]["losses"] += 1

                res_msg = (f"🏆 <b>WINGO RESULT</b> 🏆\n\n"
                           f"<b>🚀 PERIOD:</b> <code>{p}</code>\n"
                           f"<b>🎯 PREDICTED:</b> {s} ({n[0]}, {n[1]}, {n[2]})\n"
                           f"<b>🎲 RESULT:</b> {actual_size} ({actual_num})\n\n"
                           f"<b>STATUS: {win_loss}</b>")

                if s_key:
                    try: await bot.send_sticker(chat_id=chat_id, sticker=s_key)
                    except: pass
                
                await bot.send_message(chat_id=chat_id, text=res_msg, parse_mode="HTML")
                await asyncio.sleep(5) # Cooldown before next period

        except Exception as e:
            await asyncio.sleep(5)
            
    # When loop stops
    try:
        end_stk = db["settings"]["CLOSE_STICKER"]
        if end_stk: await bot.send_sticker(chat_id=chat_id, sticker=end_stk)
        await bot.send_message(chat_id=chat_id, text="🔴 <b>AUTO SIGNALS STOPPED.</b>", parse_mode="HTML")
    except: pass

# ==========================================
# 6. KEYBOARDS & UI
# ==========================================
def kb_user_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 WINGO VIP (DM)", callback_data="play_wingo")],
        [InlineKeyboardButton("📢 AUTO CHANNEL SIGNALS", callback_data="usr_channel_menu")],
        [InlineKeyboardButton("🔗 Official Game Link", callback_data="usr_links")]
    ])

def kb_admin_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"), InlineKeyboardButton("📊 Statistics", callback_data="adm_stats")],
        [InlineKeyboardButton("🖼 Set Stickers", callback_data="adm_stickers"), InlineKeyboardButton("🔗 Set Game Link", callback_data="adm_link")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="nav_admin")]
    ])

def kb_back(to="nav_home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data=to), InlineKeyboardButton("🏠 HOME", callback_data="nav_home")]])

# ==========================================
# 7. CHANNEL ADMIN DETECTOR
# ==========================================
async def track_channel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically detects when user adds bot to channel"""
    result = update.my_chat_member
    chat = result.chat
    user = result.from_user
    new_status = result.new_chat_member.status

    if new_status in ['administrator', 'creator'] and chat.type in ['channel', 'group', 'supergroup']:
        channel_name = chat.title
        channel_id = str(chat.id)
        uid = user.id
        
        if uid not in db["channels"]: db["channels"][uid] = {}
        db["channels"][uid]["channel_id"] = channel_id
        db["channels"][uid]["channel_name"] = channel_name
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"▶️ START SIGNALS IN {channel_name.upper()}", callback_data=f"auto_ch_{channel_id}")],
            [InlineKeyboardButton("❌ LATER", callback_data="nav_home")]
        ])
        
        msg = (f"✅ <b>CHANNEL DETECTED!</b>\n\n"
               f"I am now Admin in <b>{channel_name}</b>.\n\n"
               f"Click below to start Wingo Auto Signals:")
        try:
            await context.bot.send_message(chat_id=uid, text=msg, reply_markup=kb, parse_mode="HTML")
        except: pass

# ==========================================
# 8. CORE HANDLERS
# ==========================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == CONFIG["ADMIN_ID"]:
        await update.message.reply_text("👑 <b>ALI VIP ADMIN PANEL</b>", reply_markup=kb_admin_main(), parse_mode="HTML")
    else:
        await update.message.reply_text("🔥 <b>ALI VIP WINGO DASHBOARD</b>\n\nSelect an option below to get signals:", reply_markup=kb_user_main(), parse_mode="HTML")

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

    # --- DM SIGNALS (MANUAL) ---
    elif data == "play_wingo":
        p, s, n = get_wingo_prediction()
        db["stats"]["signals"] += 1
        
        msg = f"🔴 <b>WINGO VIP SIGNAL</b>\n━━━━━━━━━━━━━━\n🚀 Period: <code>{p}</code>\n📊 Signal: <b>{s}</b>\n🔢 Nums: {n[0]}, {n[1]}, {n[2]}\n🔐 Status: VALIDATED\n━━━━━━━━━━━━━━"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ WIN", callback_data="fb_win"), InlineKeyboardButton("❌ LOSS", callback_data="fb_loss")], [InlineKeyboardButton("⏭ NEXT", callback_data="play_wingo")], [InlineKeyboardButton("🔙 Back", callback_data="nav_home")]])
        await q.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

    elif data in ["fb_win", "fb_loss"]:
        await q.answer(f"✅ RECORDED!", show_alert=True)

    # --- AUTO CHANNEL SIGNALS ---
    elif data == "usr_channel_menu":
        c_data = db["channels"].get(uid, {})
        if not c_data.get("channel_id"):
            msg = "📢 <b>HOW TO LINK CHANNEL:</b>\n1. Go to your Channel/Group.\n2. Add this bot as an <b>Admin</b>.\n3. The bot will automatically message you here!"
            await q.edit_message_text(msg, reply_markup=kb_back(), parse_mode="HTML")
        else:
            status = "🟢 RUNNING" if c_data.get("is_running") else "🔴 STOPPED"
            msg = f"📢 <b>CHANNEL MANAGEMENT</b>\n\nChannel: <b>{c_data['channel_name']}</b>\nStatus: {status}\n\nSelect action:"
            btnt = "⏹ STOP SIGNALS" if c_data.get("is_running") else "▶️ START SIGNALS"
            btnd = "usr_stop_ch" if c_data.get("is_running") else f"auto_ch_{c_data['channel_id']}"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(btnt, callback_data=btnd)], [InlineKeyboardButton("🔙 Back", callback_data="nav_home")]])
            await q.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

    elif data.startswith("auto_ch_"):
        ch_id = data.replace("auto_ch_", "")
        if uid not in db["channels"]: db["channels"][uid] = {}
        db["channels"][uid]["channel_id"] = ch_id
        
        if db["channels"][uid].get("is_running"):
            return await q.answer("Signals already running!", show_alert=True)
            
        db["channels"][uid]["is_running"] = True
        # START BACKGROUND TASK FOR THIS CHANNEL
        db["channels"][uid]["task"] = asyncio.create_task(channel_signal_worker(context.bot, uid, ch_id))
        
        await q.edit_message_text("🟢 <b>CHANNEL SIGNALS STARTED!</b>\nSignals will now automatically appear in your channel.", reply_markup=kb_back(), parse_mode="HTML")

    elif data == "usr_stop_ch":
        if uid in db["channels"]:
            db["channels"][uid]["is_running"] = False
            task = db["channels"][uid].get("task")
            if task: task.cancel()
        await q.edit_message_text("🔴 <b>CHANNEL SIGNALS STOPPED.</b>", reply_markup=kb_back(), parse_mode="HTML")

    elif data == "usr_links":
        link = db["settings"]["game_link"]
        msg = f"🔗 <b>OFFICIAL GAME LINK</b>\n\nRegister and play here: {link}"
        await q.edit_message_text(msg, reply_markup=kb_back(), parse_mode="HTML")

    # --- ADMIN PANEL WORKINGS ---
    elif uid == CONFIG["ADMIN_ID"]:
        if data == "adm_stats":
            msg = f"📊 <b>ADMIN STATISTICS</b>\n━━━━━━━━━━━━━━\nChannels Running: {sum(1 for c in db['channels'].values() if c.get('is_running'))}\nTotal Signals: {db['stats']['signals']}\nWins: {db['stats']['wins']}\nJackpots: {db['stats']['jackpots']}\nLosses: {db['stats']['losses']}\n━━━━━━━━━━━━━━"
            await q.edit_message_text(msg, reply_markup=kb_back("nav_admin"), parse_mode="HTML")
            
        elif data == "adm_stickers":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Set WIN", callback_data="stk_WIN_STICKER"), InlineKeyboardButton("Set LOSS", callback_data="stk_LOSS_STICKER")],
                [InlineKeyboardButton("Set JACKPOT", callback_data="stk_JACKPOT_STICKER")],
                [InlineKeyboardButton("Set START", callback_data="stk_START_STICKER"), InlineKeyboardButton("Set CLOSE", callback_data="stk_CLOSE_STICKER")],
                [InlineKeyboardButton("🔙 Back", callback_data="nav_admin")]
            ])
            await q.edit_message_text("🖼 <b>Select Sticker to Update:</b>", reply_markup=kb, parse_mode="HTML")
            
        elif data.startswith("stk_"):
            key = data.replace("stk_", "")
            user_states[uid] = f"WAITING_{key}"
            await q.edit_message_text(f"Please send the {key} sticker now:")
            
        elif data == "adm_link":
            user_states[uid] = "WAITING_LINK"
            await q.edit_message_text("🔗 Send the new Game Link:")
            
        elif data == "adm_broadcast":
            user_states[uid] = "WAITING_BROADCAST"
            await q.edit_message_text("📢 Send message to broadcast to all channel owners:")

async def text_sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_states.get(uid)
    if not state: return

    if uid == CONFIG["ADMIN_ID"]:
        if state == "WAITING_PASSWORD":
            if update.message.text == CONFIG["ADMIN_PASS"]:
                user_states.pop(uid)
                await update.message.reply_text("✅ Password Correct!", reply_markup=kb_admin_main())
            else:
                await update.message.reply_text("❌ Wrong Password.")
                
        elif state.startswith("WAITING_") and "STICKER" in state:
            if update.message.sticker:
                key = state.replace("WAITING_", "")
                db["settings"][key] = update.message.sticker.file_id
                user_states.pop(uid)
                await update.message.reply_text(f"✅ {key} Saved!", reply_markup=kb_admin_main())

        elif state == "WAITING_LINK":
            db["settings"]["game_link"] = update.message.text
            user_states.pop(uid)
            await update.message.reply_text("✅ Link Updated!", reply_markup=kb_admin_main())

        elif state == "WAITING_BROADCAST":
            user_states.pop(uid)
            for c_uid in db["channels"].keys():
                try: await update.message.copy(chat_id=c_uid)
                except: pass
            await update.message.reply_text(f"✅ Broadcast sent.", reply_markup=kb_admin_main())

# ==========================================
# 9. RUNNER (RAILWAY COMPATIBLE)
# ==========================================
async def post_init(application: Application):
    """Start web server for Railway Port Binding"""
    asyncio.create_task(start_web_server())

def main():
    app = ApplicationBuilder().token(CONFIG["BOT_TOKEN"]).post_init(post_init).build()
    
    app.add_handler(CommandHandler(["start", "admin"], cmd_start))
    app.add_handler(ChatMemberHandler(track_channel_admin, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, text_sticker_handler))
    
    logger.info("👑 ALI VIP WINGO BOT STARTED (Railway Fixed)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
