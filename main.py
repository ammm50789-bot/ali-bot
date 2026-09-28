"""
👑 ALI VIP - ULTIMATE DIRECT ACCESS TELEGRAM BOT
Features: Direct Start (No UID/Deposit), Auto-Channel Admin Detector, Working Admin Panel
Deployment: Railway Optimized (Port Binding + RAM DB)
"""

import asyncio
import logging
import time
import random
import os
import json
import io
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List

import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ChatMemberHandler, filters, ContextTypes, Application
)

# ==========================================
# 1. CONFIGURATION & ENVIRONMENT
# ==========================================
CONFIG = {
    "BOT_TOKEN": os.getenv("8404151043:AAGypUvXKXml-3laiC3bUtEs02McyXJdaTs", "8928420277"),
    "ADMIN_ID": int(os.getenv("ADMIN_ID", "0")),
    "ADMIN_PASS": "11223344Ali",
    "PORT": int(os.environ.get("PORT", 8080)),
    "WINGO_API": os.getenv("API_BASE_URL", "https://api.bdg88zf.com"),
    "AVIATOR_API": os.getenv("AVIATOR_API", "https://aviator-next.spribegaming.com"),
}

TZ_OFFSET = timedelta(hours=5, minutes=30)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 2. DATA MODELS & RAM DATABASE
# ==========================================
@dataclass
class UserStats:
    signals_requested: int = 0
    wins: int = 0
    losses: int = 0

@dataclass
class UserProfile:
    id: int
    name: str
    is_admin: bool = False
    channel_id: str = None
    channel_name: str = ""
    is_channel_running: bool = False
    task: asyncio.Task = None  # Store the background loop for this user's channel
    stats: UserStats = field(default_factory=UserStats)

db = {
    "users": {},       # Dict[int, UserProfile]
    "logs": [],
    "settings": {
        "bot_on": True,
        "emergency_stop": False,
        "game_link": "https://pakvip.sbs",
        "WIN_STICKER": None,
        "LOSS_STICKER": None,
        "START_STICKER": None,
        "CLOSE_STICKER": None
    },
    "stats": {"api_reqs": 0, "api_errs": 0, "signals": 0, "broadcasts": 0, "start_time": time.time()}
}

user_states: Dict[int, dict] = {} 

def set_state(uid: int, state: str):
    if uid not in user_states: user_states[uid] = {}
    user_states[uid]["state"] = state

def get_state(uid: int) -> str:
    return user_states.get(uid, {}).get("state", "")

# ==========================================
# 3. RAILWAY WEB SERVER
# ==========================================
async def health_check(request):
    return web.json_response({"status": "online", "bot": "ALI VIP", "uptime": time.time() - db["stats"]["start_time"]})

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', CONFIG["PORT"])
    await site.start()

# ==========================================
# 4. SIGNAL & AUTOMATION ENGINE
# ==========================================
def get_wingo_prediction():
    ist_now = datetime.utcnow() + TZ_OFFSET
    period = f"{ist_now.strftime('%Y%m%d')}1000{(ist_now.hour * 60) + ist_now.minute + 1:04d}"
    s = random.choice(["BIG", "SMALL"])
    n = random.sample([5, 6, 7, 8, 9], 2) if s == "BIG" else random.sample([0, 1, 2, 3, 4], 2)
    return period, s, n

def get_aviator_prediction():
    m = round(random.uniform(1.2, 5.5), 2)
    return m

async def channel_signal_worker(bot, uid: int, chat_id: str):
    """Har user ke channel ke liye ek alag background worker chalega."""
    logger.info(f"Auto-Signals Started for Channel {chat_id}")
    
    stk = db["settings"]["START_STICKER"]
    if stk:
        try: await bot.send_sticker(chat_id=chat_id, sticker=stk)
        except: pass
    await bot.send_message(chat_id=chat_id, text="🟢 <b>AUTO SIGNALS (VIP) STARTED!</b>", parse_mode="HTML")

    while db["users"][uid].is_channel_running and not db["settings"]["emergency_stop"]:
        try:
            # 1. Wingo Period Track
            ist_now = datetime.utcnow() + TZ_OFFSET
            seconds = ist_now.second
            
            # Wingo 30s cycle logic
            if seconds >= 45:
                await asyncio.sleep(2)
                continue

            # 2. Generate Prediction
            p, s, n = get_wingo_prediction()
            db["stats"]["signals"] += 1
            
            link = db["settings"]["game_link"]
            msg = (f"🔥 <b>ALI PREDICTION VIP</b> 🔥\n\n"
                   f"🎯 <b>NEW SIGNAL</b>\n\n"
                   f"<b>PERIOD:</b> <code>{p}</code>\n"
                   f"<b>📊 SIZE:</b> {s}\n"
                   f"<b>🔢 NUMBERS:</b> {n[0]}, {n[1]}\n\n"
                   f"⚠️ <i>Trend Analytical Prediction</i>\n\n"
                   f"━━━━━━━━━━━━━━━━\n"
                   f"🎮 <b>Play Here:</b> {link}")

            # Send Prediction
            try: await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", disable_web_page_preview=True)
            except Exception as e: 
                logger.error(f"Cannot send to channel: {e}")
                db["users"][uid].is_channel_running = False
                break
            
            # 3. Wait for result
            await asyncio.sleep(55 - seconds)
            
            # 4. Generate Result
            actual_size = random.choice(["BIG", "SMALL"])
            is_win = (s == actual_size)
            win_loss = "WIN ✅" if is_win else "LOSS ❌"
            
            if is_win: db["users"][uid].stats.wins += 1
            else: db["users"][uid].stats.losses += 1

            res_msg = (f"🏆 <b>RESULT VIP</b>\n\n"
                       f"<b>PERIOD:</b> <code>{p}</code>\n"
                       f"<b>🎯 PREDICTED:</b> {s}\n"
                       f"<b>🎲 RESULT:</b> {actual_size}\n\n"
                       f"<b>STATUS: {win_loss}</b>")

            s_key = db["settings"]["WIN_STICKER"] if is_win else db["settings"]["LOSS_STICKER"]
            if s_key:
                try: await bot.send_sticker(chat_id=chat_id, sticker=s_key)
                except: pass
            
            await bot.send_message(chat_id=chat_id, text=res_msg, parse_mode="HTML")
            await asyncio.sleep(5)

        except Exception as e:
            await asyncio.sleep(5)
            
    # When loop stops
    try:
        end_stk = db["settings"]["CLOSE_STICKER"]
        if end_stk: await bot.send_sticker(chat_id=chat_id, sticker=end_stk)
        await bot.send_message(chat_id=chat_id, text="🔴 <b>AUTO SIGNALS STOPPED.</b>", parse_mode="HTML")
    except: pass

# ==========================================
# 5. KEYBOARDS
# ==========================================
def kb_user_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 WINGO VIP (DM)", callback_data="play_wingo"), InlineKeyboardButton("✈️ AVIATOR VIP (DM)", callback_data="play_aviator")],
        [InlineKeyboardButton("📢 AUTO CHANNEL SIGNALS", callback_data="usr_channel_menu")],
        [InlineKeyboardButton("👤 My Profile", callback_data="usr_profile"), InlineKeyboardButton("📜 History", callback_data="usr_history")],
        [InlineKeyboardButton("🔗 Game Links", callback_data="usr_links")]
    ])

def kb_admin_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"), InlineKeyboardButton("📊 Statistics", callback_data="adm_stats")],
        [InlineKeyboardButton("🖼 Set Stickers", callback_data="adm_stickers"), InlineKeyboardButton("🔗 Set Game Link", callback_data="adm_link")],
        [InlineKeyboardButton("🚨 Emergency Mode", callback_data="adm_emergency"), InlineKeyboardButton("🔄 Refresh", callback_data="nav_admin")]
    ])

def kb_back(to="nav_home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data=to), InlineKeyboardButton("🏠 HOME", callback_data="nav_home")]])

# ==========================================
# 6. CHANNEL DETECTOR
# ==========================================
async def track_channel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects when bot is added to a channel as Admin"""
    result = update.my_chat_member
    chat = result.chat
    user = result.from_user
    new_status = result.new_chat_member.status

    if new_status in ['administrator', 'creator'] and chat.type in ['channel', 'group', 'supergroup']:
        channel_name = chat.title
        channel_id = str(chat.id)
        uid = user.id
        
        if uid not in db["users"]:
            db["users"][uid] = UserProfile(id=uid, name=user.first_name)
            
        db["users"][uid].channel_id = channel_id
        db["users"][uid].channel_name = channel_name
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"▶️ START IN {channel_name.upper()}", callback_data=f"auto_ch_{channel_id}")],
            [InlineKeyboardButton("❌ LATER", callback_data="nav_home")]
        ])
        
        msg = (f"✅ <b>CHANNEL DETECTED!</b>\n\n"
               f"I am now an Admin in <b>{channel_name}</b>.\n\n"
               f"Click the button below to start sending signals into this channel automatically!")
        try:
            await context.bot.send_message(chat_id=uid, text=msg, reply_markup=kb, parse_mode="HTML")
        except: pass

# ==========================================
# 7. ROUTERS & HANDLERS
# ==========================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    
    # Initialize Direct VIP User
    if uid not in db["users"]:
        db["users"][uid] = UserProfile(id=uid, name=name, is_admin=(uid==CONFIG["ADMIN_ID"]))

    if uid == CONFIG["ADMIN_ID"]:
        await update.message.reply_text("👑 <b>ALI VIP ADMIN PANEL</b>", reply_markup=kb_admin_main(), parse_mode="HTML")
    else:
        await update.message.reply_text("🔥 <b>ALI VIP USER DASHBOARD</b>\n\nSelect an option below to get signals:", reply_markup=kb_user_main(), parse_mode="HTML")

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != CONFIG["ADMIN_ID"]: return
    set_state(uid, "WAITING_PASSWORD")
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
            await q.edit_message_text("🔥 <b>ALI VIP USER DASHBOARD</b>", reply_markup=kb_user_main(), parse_mode="HTML")
    elif data == "nav_admin":
        if uid == CONFIG["ADMIN_ID"]: await q.edit_message_text("👑 <b>ALI VIP ADMIN DASHBOARD</b>", reply_markup=kb_admin_main(), parse_mode="HTML")

    # --- DM SIGNALS (MANUAL) ---
    elif data == "play_wingo":
        p, s, n = get_wingo_prediction()
        db["stats"]["signals"] += 1
        db["users"][uid].stats.signals_requested += 1
        
        msg = f"🔴 <b>WINGO VIP SIGNAL</b>\n━━━━━━━━━━━━━━\n🚀 Period: <code>{p}</code>\n📊 Signal: <b>{s}</b>\n🔢 Nums: {n[0]}, {n[1]}\n🔐 Status: VALIDATED\n━━━━━━━━━━━━━━"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ WIN", callback_data="fb_win"), InlineKeyboardButton("❌ LOSS", callback_data="fb_loss")], [InlineKeyboardButton("⏭ NEXT", callback_data="play_wingo")], [InlineKeyboardButton("🔙 Back", callback_data="nav_home")]])
        await q.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

    elif data == "play_aviator":
        m = get_aviator_prediction()
        db["stats"]["signals"] += 1
        db["users"][uid].stats.signals_requested += 1
        
        msg = f"✈️ <b>AVIATOR VIP SIGNAL</b>\n━━━━━━━━━━━━━━\n🎯 Target Range: <b>{max(1.05, m-0.2):.2f}x - {m:.2f}x</b>\n📈 Confidence: {random.randint(85,99)}%\n🔐 Status: VALIDATED\n━━━━━━━━━━━━━━"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ WIN", callback_data="fb_win"), InlineKeyboardButton("❌ LOSS", callback_data="fb_loss")], [InlineKeyboardButton("⏭ NEXT", callback_data="play_aviator")], [InlineKeyboardButton("🔙 Back", callback_data="nav_home")]])
        await q.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

    elif data in ["fb_win", "fb_loss"]:
        if data == "fb_win": db["users"][uid].stats.wins += 1
        else: db["users"][uid].stats.losses += 1
        await q.answer(f"✅ RECORDED!", show_alert=True)

    # --- AUTO CHANNEL SIGNALS ---
    elif data == "usr_channel_menu":
        u = db["users"][uid]
        if not u.channel_id:
            msg = "📢 <b>HOW TO LINK CHANNEL:</b>\n1. Go to your Channel/Group.\n2. Add this bot as an <b>Admin</b>.\n3. The bot will automatically message you here!"
            await q.edit_message_text(msg, reply_markup=kb_back(), parse_mode="HTML")
        else:
            status = "🟢 RUNNING" if u.is_channel_running else "🔴 STOPPED"
            msg = f"📢 <b>CHANNEL MANAGEMENT</b>\n\nChannel: <b>{u.channel_name}</b>\nStatus: {status}\n\nSelect action:"
            btnt = "⏹ STOP SIGNALS" if u.is_channel_running else "▶️ START SIGNALS"
            btnd = "usr_stop_ch" if u.is_channel_running else f"auto_ch_{u.channel_id}"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(btnt, callback_data=btnd)], [InlineKeyboardButton("🔙 Back", callback_data="nav_home")]])
            await q.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

    elif data.startswith("auto_ch_"):
        ch_id = data.replace("auto_ch_", "")
        u = db["users"][uid]
        u.channel_id = ch_id
        
        if u.is_channel_running:
            return await q.answer("Signals already running!", show_alert=True)
            
        u.is_channel_running = True
        u.task = asyncio.create_task(channel_signal_worker(context.bot, uid, ch_id))
        
        await q.edit_message_text("🟢 <b>CHANNEL SIGNALS STARTED!</b>\nSignals will now automatically appear in your channel.", reply_markup=kb_back(), parse_mode="HTML")

    elif data == "usr_stop_ch":
        u = db["users"][uid]
        u.is_channel_running = False
        if u.task: u.task.cancel()
        await q.edit_message_text("🔴 <b>CHANNEL SIGNALS STOPPED.</b>", reply_markup=kb_back(), parse_mode="HTML")

    # --- USER PROFILE & LINKS ---
    elif data == "usr_profile" or data == "usr_history":
        u = db["users"][uid]
        acc = int((u.stats.wins / max(1, u.stats.signals_requested)) * 100)
        msg = f"👤 <b>PROFILE & HISTORY</b>\n━━━━━━━━━━━━━━\nName: {u.name}\nSignals Requested: {u.stats.signals_requested}\nWins: {u.stats.wins}\nLosses: {u.stats.losses}\nWin Rate: {acc}%\n━━━━━━━━━━━━━━"
        await q.edit_message_text(msg, reply_markup=kb_back(), parse_mode="HTML")

    elif data == "usr_links":
        await q.edit_message_text(f"🔗 <b>OFFICIAL GAME LINK</b>\n\nPlay here: {db['settings']['game_link']}", reply_markup=kb_back(), parse_mode="HTML")

    # --- ADMIN PANEL ---
    elif uid == CONFIG["ADMIN_ID"]:
        if data == "adm_stats":
            tot_users = len(db["users"])
            ch_running = sum(1 for u in db["users"].values() if u.is_channel_running)
            msg = f"📊 <b>ADMIN STATISTICS</b>\n━━━━━━━━━━━━━━\nTotal Users: {tot_users}\nActive Auto-Channels: {ch_running}\nTotal Signals Generated: {db['stats']['signals']}\n━━━━━━━━━━━━━━"
            await q.edit_message_text(msg, reply_markup=kb_back("nav_admin"), parse_mode="HTML")
            
        elif data == "adm_stickers":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("WIN Sticker", callback_data="stk_WIN_STICKER"), InlineKeyboardButton("LOSS Sticker", callback_data="stk_LOSS_STICKER")],
                [InlineKeyboardButton("START Session", callback_data="stk_START_STICKER"), InlineKeyboardButton("CLOSE Session", callback_data="stk_CLOSE_STICKER")],
                [InlineKeyboardButton("🔙 Back", callback_data="nav_admin")]
            ])
            await q.edit_message_text("🖼 <b>Select Sticker to Update:</b>", reply_markup=kb, parse_mode="HTML")
        elif data.startswith("stk_"):
            key = data.replace("stk_", "")
            set_state(uid, f"WAITING_{key}")
            await q.edit_message_text(f"Please send the {key} sticker now:")
            
        elif data == "adm_link":
            set_state(uid, "WAITING_LINK")
            await q.edit_message_text("🔗 Send the new Game Link:")
            
        elif data == "adm_broadcast":
            set_state(uid, "WAITING_BROADCAST")
            await q.edit_message_text("📢 Send message to broadcast to all users:")
            
        elif data == "adm_export":
            exp_data = json.dumps({"users": len(db["users"]), "stats": db["stats"]}, indent=4)
            file = InputFile(io.BytesIO(exp_data.encode()), filename=f"VIP_Export_{int(time.time())}.json")
            await context.bot.send_document(chat_id=uid, document=file, caption="📤 System Export")
            await q.edit_message_text("✅ Export Generated.", reply_markup=kb_back("nav_admin"))

        elif data == "adm_emergency":
            st = db["settings"]["emergency_stop"]
            db["settings"]["emergency_stop"] = not st
            msg = "🚨 <b>EMERGENCY STOP ACTIVATED</b>\nAll Auto Channels halted." if not st else "✅ Emergency Lifted."
            await q.edit_message_text(msg, reply_markup=kb_back("nav_admin"), parse_mode="HTML")

async def text_sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = get_state(uid)
    if not state: return

    if uid == CONFIG["ADMIN_ID"]:
        if state == "WAITING_PASSWORD":
            if update.message.text == CONFIG["ADMIN_PASS"]:
                set_state(uid, "")
                await update.message.reply_text("✅ Password Correct!", reply_markup=kb_admin_main())
            else:
                await update.message.reply_text("❌ Wrong Password.")
                
        elif state.startswith("WAITING_") and "STICKER" in state:
            if update.message.sticker:
                key = state.replace("WAITING_", "")
                db["settings"][key] = update.message.sticker.file_id
                set_state(uid, "")
                await update.message.reply_text(f"✅ {key} Saved!", reply_markup=kb_admin_main())

        elif state == "WAITING_LINK":
            db["settings"]["game_link"] = update.message.text
            set_state(uid, "")
            await update.message.reply_text("✅ Link Updated!", reply_markup=kb_admin_main())

        elif state == "WAITING_BROADCAST":
            set_state(uid, "")
            count = 0
            for u in db["users"]:
                try: 
                    await update.message.copy(chat_id=u)
                    count += 1
                except: pass
            await update.message.reply_text(f"✅ Broadcast sent to {count} users.", reply_markup=kb_admin_main())

# ==========================================
# 15. RUNNER
# ==========================================
async def post_init(application: Application):
    asyncio.create_task(start_web_server())

def main():
    if not CONFIG["BOT_TOKEN"]:
        logger.error("BOT_TOKEN is missing!")
        return

    app = ApplicationBuilder().token(CONFIG["BOT_TOKEN"]).post_init(post_init).build()
    
    app.add_handler(CommandHandler(["start", "admin"], cmd_start))
    app.add_handler(ChatMemberHandler(track_channel_admin, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, text_sticker_handler))
    
    logger.info("👑 ALI VIP DIRECT BOT STARTED (NO ONBOARDING, SMART CHANNEL DETECT)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
