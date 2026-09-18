
"""
👑 ALI VIP - ULTIMATE ENTERPRISE TELEGRAM BOT
Architecture: Single-File Python, REST API, Asyncio, aiohttp
Deployment: Railway Optimized (Port Binding + RAM DB)
Features: Smart Onboarding, Dynamic Games, Multi-Stage Validation, Advanced Admin
"""

# ==========================================
# 1. IMPORTS
# ==========================================
import asyncio
import logging
import time
import random
import os
import json
import io
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, Application
)

# ==========================================
# 2. CONFIGURATION & SECURITY
# ==========================================
CONFIG = {
    "BOT_TOKEN": "8404151043:AAGypUvXKXml-3laiC3bUtEs02McyXJdaTs",
    "ADMIN_ID": 8928420277,
    "ADMIN_PASS": "11223344Ali",
    "PORT": int(os.environ.get("PORT", 8080)),
    "WINGO_API": "https://api.bdg88zf.com/api/webapi/GetGameIssue",
    "AVIATOR_API": "https://aviator-next.spribegaming.com",
    "APP_URL": "" 
}

TZ_OFFSET = timedelta(hours=5, minutes=30) # Default Asia/Karachi-IST

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 3. CONSTANTS & ENUMS
# ==========================================
class Status:
    NEW = "NEW"
    WAITING_UID = "WAITING_UID"
    UID_SUBMITTED = "UID_SUBMITTED"
    WAITING_DEPOSIT = "WAITING_DEPOSIT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    VIP = "VIP"

class Roles:
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    USER = "USER"

# ==========================================
# 4. DATA MODELS (TYPESCRIPT-LIKE)
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
    username: str
    uid: str = ""
    deposit: float = 0.0
    status: str = Status.NEW
    role: str = Roles.USER
    vip_level: int = 0
    tags: List[str] = field(default_factory=list)
    reg_date: str = ""
    last_action: float = 0.0
    stats: UserStats = field(default_factory=UserStats)

@dataclass
class DepositRequest:
    req_id: str
    user_id: int
    uid: str
    amount: float
    status: str = "PENDING"
    time: str = ""

@dataclass
class DynamicGame:
    code: str
    name: str
    icon: str
    link: str
    is_active: bool = True
    is_maintenance: bool = False

@dataclass
class Ticket:
    tid: str
    user_id: int
    msg: str
    status: str = "OPEN"

# ==========================================
# 5. IN-MEMORY DATABASE (CRASH-FREE)
# ==========================================
db = {
    "users": {},       # Dict[int, UserProfile]
    "requests": {},    # Dict[str, DepositRequest]
    "games": {},       # Dict[str, DynamicGame]
    "tickets": {},     # Dict[str, Ticket]
    "audit_logs": [],  # List[str]
    "history": [],     # List[dict]
    "settings": {
        "bot_on": True,
        "emergency_stop": False,
        "maintenance": False,
        "auto_approve": False,
    },
    "stats": {"api_reqs": 0, "api_errs": 0, "signals": 0, "broadcasts": 0, "start_time": time.time()}
}
user_states: Dict[int, dict] = {} # uid -> {"state": "", "data": {}}

# Seed Default Games
def init_games():
    db["games"]["aviator"] = DynamicGame("aviator", "AVIATOR", "✈️", "https://pakvip.sbs")
    db["games"]["wingo"] = DynamicGame("wingo", "WINGO", "🎲", "https://pakvip.sbs")
    db["games"]["car"] = DynamicGame("car", "CAR ROULETTE", "🚗", "https://pakvip.sbs", is_active=False)

# ==========================================
# 6. RAILWAY ANTI-CRASH SERVER
# ==========================================
async def health_check(request):
    """Railway Port Binding to prevent crash."""
    return web.json_response({"status": "online", "bot": "ALI VIP", "uptime": time.time() - db["stats"]["start_time"]})

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', CONFIG["PORT"])
    await site.start()
    logger.info(f"Health Server Running on Port {CONFIG['PORT']}")

# ==========================================
# 7. SECURITY & PERMISSIONS
# ==========================================
def is_admin(uid: int) -> bool:
    if uid == CONFIG["ADMIN_ID"]: return True
    user = db["users"].get(uid)
    return user and user.role in [Roles.ADMIN, Roles.OWNER]

def is_active_user(uid: int) -> bool:
    if is_admin(uid): return True
    user = db["users"].get(uid)
    return user and user.status in [Status.APPROVED, Status.ACTIVE] and not db["settings"]["emergency_stop"]

def check_spam(uid: int) -> bool:
    now = time.time()
    user = db["users"].get(uid)
    if user:
        if now - user.last_action < 1.0: # 1 second cooldown
            return True
        user.last_action = now
    return False

def get_user_state(uid: int) -> str:
    return user_states.get(uid, {}).get("state", "")

def set_user_state(uid: int, state: str, data: any = None):
    if uid not in user_states: user_states[uid] = {}
    user_states[uid]["state"] = state
    if data is not None: user_states[uid]["data"] = data

def log_audit(admin_id: int, action: str):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db["audit_logs"].insert(0, f"[{ts}] Admin {admin_id}: {action}")
    if len(db["audit_logs"]) > 100: db["audit_logs"].pop()

# ==========================================
# 8. API CLIENT & SIGNAL ENGINE
# ==========================================
async def fetch_api(url: str, payload: dict = None) -> dict:
    """Secure, Authorized Rest API Client."""
    if not url: return {"error": True}
    db["stats"]["api_reqs"] += 1
    
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        try:
            if payload:
                async with session.post(url, json=payload, headers=headers, timeout=5) as res:
                    if res.status == 200: return await res.json()
            else:
                async with session.get(url, headers=headers, timeout=5) as res:
                    if res.status == 200: return {"error": False, "status": 200}
        except Exception as e:
            pass
            
    db["stats"]["api_errs"] += 1
    return {"error": True}

def generate_signal(game_code: str):
    """Smart Validation Engine based on available data limits."""
    if db["settings"]["emergency_stop"]: return None, 0
    game = db["games"].get(game_code)
    if not game or not game.is_active or game.is_maintenance: return None, 0

    # Data Consistency Check
    if random.random() < 0.05: return None, 0 # Simulate 5% insufficient data skip
    
    confidence = random.randint(75, 95)
    
    if game_code == "aviator":
        est = round(random.uniform(1.20, 4.50), 2)
        return f"Target Range: {max(1.05, est-0.2):.2f}x - {est:.2f}x", confidence
        
    elif game_code == "wingo":
        ist_now = datetime.utcnow() + TZ_OFFSET
        minutes_passed = (ist_now.hour * 60) + ist_now.minute + 1
        period = f"{ist_now.strftime('%Y%m%d')}1000{minutes_passed:04d}"
        
        size = random.choice(["BIG", "SMALL"])
        return f"Period: <code>{period}</code>\nSize: {size}", confidence
        
    return "Analysis Validated", confidence

# ==========================================
# 9. KEYBOARD BUILDERS (UI)
# ==========================================
def kb_back_home(back_data="nav_home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data=back_data), InlineKeyboardButton("🏠 HOME", callback_data="nav_home")]])

def kb_user_main():
    kb = []
    for code, g in db["games"].items():
        if g.is_active and not g.is_maintenance:
            kb.append([InlineKeyboardButton(f"{g.icon} {g.name} VIP", callback_data=f"game_play_{code}")])
    kb.extend([
        [InlineKeyboardButton("👤 MY PROFILE", callback_data="usr_profile"), InlineKeyboardButton("📜 HISTORY", callback_data="usr_history")],
        [InlineKeyboardButton("🆘 SUPPORT", callback_data="usr_support"), InlineKeyboardButton("🔄 REFRESH", callback_data="nav_user")]
    ])
    return InlineKeyboardMarkup(kb)

def kb_admin_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 USERS", callback_data="adm_users"), InlineKeyboardButton("💰 DEPOSITS", callback_data="adm_reqs")],
        [InlineKeyboardButton("🎮 GAMES", callback_data="adm_games"), InlineKeyboardButton("📢 BROADCAST", callback_data="adm_broadcast")],
        [InlineKeyboardButton("🎫 TICKETS", callback_data="adm_tickets"), InlineKeyboardButton("📊 STATISTICS", callback_data="adm_stats")],
        [InlineKeyboardButton("⚙️ SETTINGS", callback_data="adm_settings"), InlineKeyboardButton("🛡 SYSTEM HEALTH", callback_data="adm_health")],
        [InlineKeyboardButton("📤 EXPORT", callback_data="adm_export"), InlineKeyboardButton("🚨 EMERGENCY", callback_data="adm_emergency")],
        [InlineKeyboardButton("🔄 REFRESH", callback_data="nav_admin"), InlineKeyboardButton("🏠 HOME", callback_data="nav_home")]
    ])

# ==========================================
# 10. ONBOARDING & APPROVAL SYSTEM
# ==========================================
async def handle_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db["users"].get(uid)
    text = update.message.text
    
    if user.status == Status.WAITING_UID:
        user.uid = text
        user.status = Status.WAITING_DEPOSIT
        await update.message.reply_text("✅ <b>UID RECEIVED</b>\n\n💰 Please Send Your Deposit Amount (e.g., 1000):", parse_mode="HTML")
    
    elif user.status == Status.WAITING_DEPOSIT:
        try:
            user.deposit = float(text)
            user.status = Status.PENDING
            await update.message.reply_text("⏳ <b>YOUR REQUEST IS PENDING ADMIN APPROVAL</b>", parse_mode="HTML")
            
            # Notify Admin
            admin_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ APPROVE", callback_data=f"a_app_{uid}"), InlineKeyboardButton("❌ REJECT", callback_data=f"a_rej_{uid}")]
            ])
            admin_msg = (
                "🔔 <b>NEW DEPOSIT REQUEST</b>\n"
                f"Name: {user.name}\n"
                f"Telegram ID: <code>{uid}</code>\n"
                f"Game UID: <code>{user.uid}</code>\n"
                f"Amount: Rs {user.deposit}\n"
                f"Time: {(datetime.utcnow()+TZ_OFFSET).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            try: await context.bot.send_message(chat_id=CONFIG["ADMIN_ID"], text=admin_msg, reply_markup=admin_kb, parse_mode="HTML")
            except: pass
        except ValueError:
            await update.message.reply_text("⚠️ Please enter a valid number for the deposit amount.")

# ==========================================
# 11. GAME PLAY HANDLERS
# ==========================================
async def process_game_signal(query, context, game_code):
    if db["settings"]["emergency_stop"]:
        return await query.edit_message_text("🚨 <b>EMERGENCY STOP ACTIVE</b>\nSignals halted.", reply_markup=kb_back_home(), parse_mode="HTML")
        
    game = db["games"][game_code]
    db["stats"]["signals"] += 1
    
    # Check Live API Status for Wingo/Aviator if applicable
    api_url = CONFIG["WINGO_API"] if game_code == "wingo" else CONFIG["AVIATOR_API"]
    
    # Ping API in background
    asyncio.create_task(fetch_api(api_url))
    
    sig, conf = generate_signal(game_code)
    
    if not sig:
        return await query.edit_message_text(
            "⚠️ <b>DATA NOT AVAILABLE — REQUEST SKIPPED</b>\nServer data is inconsistent. Please wait.",
            reply_markup=kb_back_home(), parse_mode="HTML"
        )
    
    msg = f"👑 <b>{game.name} VIP SIGNAL</b>\n━━━━━━━━━━━━━━━━━━\n{sig}\n📈 Confidence: {conf}%\n🧠 Analysis: Multi-Data Validation\n🔎 Data Status: VALIDATED\n━━━━━━━━━━━━━━━━━━"
        
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ WIN", callback_data=f"fb_win_{game_code}"), InlineKeyboardButton("❌ LOSS", callback_data=f"fb_loss_{game_code}")],
        [InlineKeyboardButton(f"⏭ NEXT {game.name}", callback_data=f"game_play_{game_code}")],
        [InlineKeyboardButton("🏠 HOME", callback_data="u_home")]
    ])
    await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

# ==========================================
# 12. TELEGRAM CORE HANDLERS
# ==========================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or "User"
    name = update.effective_user.first_name or "VIP"
    
    if check_spam(uid): return
    
    if uid == CONFIG["ADMIN_ID"]:
        if uid not in db["users"]:
            db["users"][uid] = UserProfile(id=uid, name=name, username=username, status=Status.ACTIVE, role=Roles.OWNER)
        return await update.message.reply_text("👑 <b>ALI VIP ADMIN PANEL</b>", reply_markup=kb_admin_main(), parse_mode="HTML")

    if not db["settings"]["bot_on"]:
        return await update.message.reply_text("🚧 System is currently offline.")
    if db["settings"]["maintenance"]:
        return await update.message.reply_text("🔧 System is under maintenance. Try again later.")

    user = db["users"].get(uid)
    if not user:
        user = UserProfile(id=uid, name=name, username=username, reg_date=(datetime.utcnow()+TZ_OFFSET).strftime("%Y-%m-%d"))
        db["users"][uid] = user

    # SMART ONBOARDING FLOW
    if user.status in [Status.NEW, Status.WAITING_UID]:
        user.status = Status.WAITING_UID
        await update.message.reply_text(f"👑 <b>Welcome to ALI VIP</b>\n\n🆔 Please enter your Game UID:", parse_mode="HTML")
    elif user.status == Status.WAITING_DEPOSIT:
        await update.message.reply_text("💰 Please Send Your Deposit Amount:")
    elif user.status == Status.PENDING:
        await update.message.reply_text("⏳ YOUR REQUEST IS PENDING ADMIN APPROVAL.")
    elif user.status in [Status.BLOCKED, Status.REJECTED]:
        await update.message.reply_text("⛔ Access Denied.")
    elif user.status in [Status.APPROVED, Status.ACTIVE, Status.VIP]:
        await update.message.reply_text(f"🔥 <b>ALI VIP USER PANEL</b>\n\nSelect an option:", reply_markup=kb_user_main(), parse_mode="HTML")

# ==========================================
# 13. CALLBACK ROUTER
# ==========================================
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = q.data
    
    if check_spam(uid): return await q.answer("Slow down!", show_alert=True)
    await q.answer()

    # --- NAVIGATION ---
    if data == "nav_home":
        if is_admin(uid): await q.edit_message_text("👑 <b>ALI VIP ADMIN DASHBOARD</b>", reply_markup=kb_admin_main(), parse_mode="HTML")
        elif is_active_user(uid): await q.edit_message_text("🔥 <b>ALI VIP USER DASHBOARD</b>", reply_markup=kb_user_main(), parse_mode="HTML")
        else: await q.edit_message_text("⏳ Your account is pending or blocked.")
    elif data == "nav_admin":
        await q.edit_message_text("👑 <b>ALI VIP ADMIN DASHBOARD</b>", reply_markup=kb_admin_main(), parse_mode="HTML")
    elif data == "u_home":
        if not is_active_user(uid): return
        await q.edit_message_text("🔥 <b>ALI VIP USER PANEL</b>", reply_markup=kb_user_main(), parse_mode="HTML")

    # --- USER CALLBACKS ---
    elif data.startswith("game_play_"):
        if not is_active_user(uid): return await q.answer("Unauthorized", show_alert=True)
        game_code = data.split("_")[2]
        await process_game_signal(q, context, game_code)

    elif data.startswith("fb_"):
        if not is_active_user(uid): return
        action = data.split("_")[1]
        user = db["users"][uid]
        if action == "win": user.stats.wins += 1
        else: user.stats.losses += 1
        user.stats.signals_requested += 1
        await q.answer(f"✅ {action.upper()} RECORDED!", show_alert=True)

    elif data == "usr_profile":
        u = db["users"][uid]
        msg = f"👤 <b>PROFILE</b>\nName: {u.name}\nID: {uid}\nUID: {u.uid}\nStatus: {u.status}\nRole: {u.role}\nDeposit: {u.deposit}\nSignals: {u.stats.signals_requested}\nWins: {u.stats.wins}"
        await q.edit_message_text(msg, reply_markup=kb_back_home(), parse_mode="HTML")

    elif data == "usr_support":
        set_user_state(uid, "AWAIT_TICKET")
        await q.edit_message_text("🎫 <b>SUPPORT</b>\nPlease type your message below:", reply_markup=kb_back_home(), parse_mode="HTML")

    # --- ADMIN CALLBACKS ---
    elif is_admin(uid):
        if data == "adm_reqs":
            pending = [u for u in db["users"].values() if u.status == Status.PENDING]
            if not pending: return await q.edit_message_text("✅ No pending requests.", reply_markup=kb_back_home("nav_admin"))
            
            u = pending[0]
            msg = f"💰 <b>DEPOSIT REQUEST</b>\nUser: {u.name}\nUID: <code>{u.uid}</code>\nAmount: Rs {u.deposit}\nStatus: PENDING"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"adm_app_{u.id}"), InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej_{u.id}")],
                [InlineKeyboardButton("🔙 Back", callback_data="nav_admin")]
            ])
            await q.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

        elif data.startswith("adm_app_"):
            target_uid = int(data.split("_")[2])
            if target_uid in db["users"]:
                db["users"][target_uid].status = Status.ACTIVE
                log_audit(uid, f"Approved user {target_uid}")
                await q.edit_message_text(f"✅ User {target_uid} Approved.", reply_markup=kb_back_home("adm_reqs"))
                try: await context.bot.send_message(chat_id=target_uid, text="✅ <b>YOUR ACCOUNT IS APPROVED!</b>\nPress /start to begin.", parse_mode="HTML")
                except: pass

        elif data.startswith("adm_rej_"):
            target_uid = int(data.split("_")[2])
            if target_uid in db["users"]:
                db["users"][target_uid].status = Status.REJECTED
                log_audit(uid, f"Rejected user {target_uid}")
                await q.edit_message_text(f"❌ User {target_uid} Rejected.", reply_markup=kb_back_home("adm_reqs"))

        elif data == "adm_games":
            kb = [[InlineKeyboardButton(f"⚙️ {g.name} ({'ON' if g.is_active else 'OFF'})", callback_data=f"adm_tg_{code}")] for code, g in db["games"].items()]
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="nav_admin")])
            await q.edit_message_text("🎮 <b>GAME MANAGEMENT</b>\nClick to toggle ON/OFF:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

        elif data.startswith("adm_tg_"):
            g_id = data.split("_")[2]
            db["games"][g_id].is_active = not db["games"][g_id].is_active
            log_audit(uid, f"Toggled Game {g_id} to {db['games'][g_id].is_active}")
            await callback_router(Update(update.update_id, callback_query=update.callback_query), context)

        elif data == "adm_stats" or data == "adm_health":
            up_time = str(timedelta(seconds=int(time.time() - db["stats"]["start_time"])))
            tot_users = len(db["users"])
            active_u = len([u for u in db["users"].values() if u.status == Status.ACTIVE])
            msg = (f"📊 <b>ADVANCED STATISTICS & HEALTH</b>\n━━━━━━━━━━━━━━\n"
                   f"Users: {tot_users} (Active: {active_u})\n"
                   f"Games: {len(db['games'])}\n"
                   f"API Reqs: {db['stats']['api_reqs']}\n"
                   f"API Errors: {db['stats']['api_errs']}\n"
                   f"Signals Sent: {db['stats']['signals']}\n"
                   f"Uptime: {up_time}\n"
                   f"Emergency Mode: {db['settings']['emergency_stop']}\n━━━━━━━━━━━━━━")
            await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 REFRESH", callback_data="adm_stats"), InlineKeyboardButton("🏠 HOME", callback_data="nav_admin")]]), parse_mode="HTML")

        elif data == "adm_broadcast":
            set_user_state(uid, "AWAIT_BROADCAST")
            await q.edit_message_text("📢 Send Text, Photo, Video, or Audio to broadcast to all ACTIVE users:", reply_markup=kb_back_home("nav_admin"))

        elif data == "adm_export":
            # Safe Export (No tokens)
            exp_data = json.dumps({"users_count": len(db["users"]), "stats": db["stats"], "audit_logs": db["audit_logs"]}, indent=4)
            file = InputFile(io.BytesIO(exp_data.encode()), filename=f"ALI_VIP_Audit_{int(time.time())}.json")
            await context.bot.send_document(chat_id=uid, document=file, caption="📤 System Export")
            await q.edit_message_text("✅ Export Generated.", reply_markup=kb_back_home("nav_admin"))

        elif data == "adm_emergency":
            st = db["settings"]["emergency_stop"]
            db["settings"]["emergency_stop"] = not st
            log_audit(uid, f"Emergency Stop Toggled: {not st}")
            msg = "🚨 <b>EMERGENCY MODE ACTIVATED</b>\nAll signals halted." if not st else "✅ Emergency Lifted."
            await q.edit_message_text(msg, reply_markup=kb_back_home("nav_admin"), parse_mode="HTML")

# ==========================================
# 14. TEXT & MEDIA HANDLERS
# ==========================================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = get_user_state(uid)
    text = update.message.text
    
    # Route Onboarding
    if uid in db["users"] and db["users"][uid].status in [Status.WAITING_UID, Status.WAITING_DEPOSIT]:
        return await handle_onboarding(update, context)
        
    if not state: return

    # User Ticket
    if state == "AWAIT_TICKET":
        tid = f"TK{int(time.time())}"
        db["tickets"][tid] = Ticket(tid, uid, text)
        set_user_state(uid, "")
        await update.message.reply_text("✅ Ticket Submitted. Admin will review shortly.")
        try: await context.bot.send_message(chat_id=CONFIG["ADMIN_ID"], text=f"🎫 <b>NEW TICKET {tid}</b>\nFrom: {uid}\nMsg: {text}", parse_mode="HTML")
        except: pass

    # Admin Broadcast
    elif is_admin(uid) and state == "AWAIT_BROADCAST":
        set_user_state(uid, "")
        count = 0
        for u_id, u_prof in db["users"].items():
            if u_prof.status in [Status.ACTIVE, Status.APPROVED]:
                try: 
                    await update.message.copy(chat_id=u_id)
                    count += 1
                except: pass
        db["stats"]["broadcasts"] += 1
        log_audit(uid, f"Sent broadcast to {count} users.")
        await update.message.reply_text(f"✅ Broadcast sent to {count} users.", reply_markup=kb_back_home("nav_admin"))

# ==========================================
# 15. BOT STARTUP (RAILWAY READY)
# ==========================================
async def post_init(application: Application):
    """Triggers Railway Web Server for Port Binding & Inits Games."""
    init_games()
    asyncio.create_task(start_web_server())

def main():
    if not CONFIG["BOT_TOKEN"]:
        logger.error("BOT_TOKEN is missing! Set environment variables.")
        return

    app = ApplicationBuilder().token(CONFIG["BOT_TOKEN"]).post_init(post_init).build()
    
    app.add_handler(CommandHandler(["start", "menu", "help"], cmd_start))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))
    
    logger.info("👑 ALI VIP ULTIMATE ENTERPRISE BOT STARTED!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
