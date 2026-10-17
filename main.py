import os, sqlite3, logging
from decimal import Decimal, InvalidOperation
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MIN_WITHDRAW = Decimal(os.getenv("MIN_WITHDRAW", "5"))
CURRENCY = os.getenv("REWARD_CURRENCY", "USDT")
DB = os.getenv("DB_PATH", "bot.sqlite3")
logging.basicConfig(level=logging.INFO)

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, referrer INTEGER, balance TEXT DEFAULT '0');
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, url TEXT, reward TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_id INTEGER, status TEXT DEFAULT 'pending', UNIQUE(user_id,task_id));
        CREATE TABLE IF NOT EXISTS withdrawals(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount TEXT, pay_id TEXT, status TEXT DEFAULT 'pending');
        CREATE TABLE IF NOT EXISTS ref_paid(user_id INTEGER PRIMARY KEY);
        """)
        if c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
            c.execute("INSERT INTO tasks(title,url,reward) VALUES(?,?,?)",
                      ("Demo task — replace this", "https://example.com", "0.10"))

def fmt(x): return f"{Decimal(x):.2f} {CURRENCY}"
def user(uid):
    with conn() as c: return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 ভিডিও টাস্ক", callback_data="tasks"), InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance")],
        [InlineKeyboardButton("👥 রেফারেল", callback_data="ref"), InlineKeyboardButton("💸 উইথড্র নির্দেশনা", callback_data="wd")],
        [InlineKeyboardButton("ℹ️ নিয়ম", callback_data="rules")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ref = None
    if context.args and context.args[0].startswith("ref_"):
        try: ref = int(context.args[0][4:])
        except ValueError: pass
    if ref == u.id: ref = None
    with conn() as c:
        exists = c.execute("SELECT id FROM users WHERE id=?", (u.id,)).fetchone()
        if not exists:
            if ref and not c.execute("SELECT id FROM users WHERE id=?", (ref,)).fetchone(): ref = None
            c.execute("INSERT INTO users(id,username,first_name,referrer) VALUES(?,?,?,?)",
                      (u.id, u.username or "", u.first_name or "", ref))
        else:
            c.execute("UPDATE users SET username=?,first_name=? WHERE id=?", (u.username or "", u.first_name or "", u.id))
    await update.message.reply_text(
        f"স্বাগতম {u.first_name or ''}!\\nএটি একটি ডেমো Video Earn & Rewards Bot। টাস্ক অনুমোদনের পর রিওয়ার্ড যোগ হবে।\\n"
        f"ন্যূনতম উইথড্র: {fmt(MIN_WITHDRAW)}\\nস্বয়ংক্রিয় Binance পেমেন্ট চালু নেই।",
        reply_markup=menu())

async def click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); uid = q.from_user.id
    if q.data == "balance":
        u = user(uid); await q.message.reply_text(f"আপনার ডেমো ব্যালেন্স: {fmt(u['balance'] if u else '0')}")
    elif q.data == "tasks":
        with conn() as c:
            tasks = c.execute("SELECT * FROM tasks WHERE active=1").fetchall()
            subs = {r["task_id"]:r["status"] for r in c.execute("SELECT task_id,status FROM submissions WHERE user_id=?", (uid,))}
        if not tasks: await q.message.reply_text("এখন কোনো টাস্ক নেই।"); return
        for t in tasks:
            if t["id"] in subs:
                await q.message.reply_text(f"{t['title']} — {subs[t['id']]}")
            else:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("ভিডিও খুলুন", url=t["url"])],
                    [InlineKeyboardButton("দেখা শেষ — যাচাইয়ের জন্য জমা", callback_data=f"submit_{t['id']}")]])
                await q.message.reply_text(f"🎬 {t['title']}\\nরিওয়ার্ড: {fmt(t['reward'])}", reply_markup=kb)
    elif q.data.startswith("submit_"):
        tid = int(q.data.split("_")[1])
        with conn() as c:
            t = c.execute("SELECT * FROM tasks WHERE id=? AND active=1", (tid,)).fetchone()
            if not t: await q.message.reply_text("টাস্ক পাওয়া যায়নি।"); return
            try: c.execute("INSERT INTO submissions(user_id,task_id) VALUES(?,?)", (uid,tid))
            except sqlite3.IntegrityError: await q.message.reply_text("এই টাস্ক আগেই জমা দিয়েছেন।"); return
            sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        await q.message.reply_text("জমা হয়েছে। অ্যাডমিন যাচাই ও অনুমোদন না করা পর্যন্ত ব্যালেন্সে যোগ হবে না।")
        if ADMIN_ID:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ অনুমোদন", callback_data=f"approve_{sid}"),
                                        InlineKeyboardButton("❌ প্রত্যাখ্যান", callback_data=f"reject_{sid}")]])
            await context.bot.send_message(ADMIN_ID, f"টাস্ক জমা\\nUser: {uid}\\nTask: {t['title']}\\nReward: {fmt(t['reward'])}", reply_markup=kb)
    elif q.data == "ref":
        me = await context.bot.get_me()
        await q.message.reply_text(f"আপনার রেফারেল লিংক:\\nhttps://t.me/{me.username}?start=ref_{uid}\\n"
            "প্রথম টাস্ক অনুমোদিত হলে রেফারেল বোনাস যোগ হবে।")
    elif q.data == "wd":
        await q.message.reply_text("উইথড্র রিকোয়েস্ট: /withdraw পরিমাণ BinancePayID\\nউদাহরণ: /withdraw 5.00 my_pay_id\\n"
            f"ন্যূনতম {fmt(MIN_WITHDRAW)}। এই সংস্করণে Binance-এ স্বয়ংক্রিয় পেমেন্ট নেই।")
    elif q.data == "rules":
        await q.message.reply_text("• রিওয়ার্ড অ্যাডমিন যাচাইয়ের পরে যোগ হবে।\\n• কোনো নিশ্চিত আয়ের প্রতিশ্রুতি নেই।\\n"
            "• উইথড্র রিকোয়েস্ট ম্যানুয়ালি যাচাই হবে।\\n• Binance password, 2FA, seed phrase বা API secret কখনো দেবেন না।")
    elif q.data.startswith(("approve_", "reject_")):
        if uid != ADMIN_ID or not ADMIN_ID: await q.message.reply_text("শুধু অ্যাডমিনের জন্য।"); return
        action, sid = q.data.split("_"); sid = int(sid)
        with conn() as c:
            s = c.execute("SELECT s.*,t.reward,u.referrer FROM submissions s JOIN tasks t ON t.id=s.task_id JOIN users u ON u.id=s.user_id WHERE s.id=?", (sid,)).fetchone()
            if not s or s["status"] != "pending": await q.message.reply_text("ইতোমধ্যে প্রক্রিয়া করা হয়েছে।"); return
            c.execute("UPDATE submissions SET status=? WHERE id=?", ("approved" if action=="approve" else "rejected",sid))
            if action == "approve":
                bal = Decimal(c.execute("SELECT balance FROM users WHERE id=?", (s["user_id"],)).fetchone()[0])
                c.execute("UPDATE users SET balance=? WHERE id=?", (str(bal+Decimal(s["reward"])),s["user_id"]))
                if s["referrer"]:
                    prev = c.execute("SELECT 1 FROM ref_paid WHERE user_id=?", (s["user_id"],)).fetchone()
                    if not prev:
                        rb = Decimal(c.execute("SELECT balance FROM users WHERE id=?", (s["referrer"],)).fetchone()[0])
                        c.execute("UPDATE users SET balance=? WHERE id=?", (str(rb+Decimal("0.10")),s["referrer"]))
                        c.execute("INSERT INTO ref_paid(user_id) VALUES(?)", (s["user_id"],))
        await context.bot.send_message(s["user_id"], "টাস্ক অনুমোদিত হয়েছে এবং রিওয়ার্ড যোগ হয়েছে।" if action=="approve" else "টাস্ক অনুমোদিত হয়নি।")
        await q.message.reply_text("সম্পন্ন।")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("ব্যবহার: /withdraw 5.00 BinancePayID"); return
    try: amount = Decimal(context.args[0])
    except InvalidOperation: await update.message.reply_text("সঠিক পরিমাণ দিন।"); return
    if not amount.is_finite() or amount <= 0: await update.message.reply_text("পরিমাণ অবশ্যই শূন্যের বেশি হতে হবে।"); return
    u = user(uid)
    if not u: await update.message.reply_text("প্রথমে /start দিন।"); return
    bal = Decimal(u["balance"])
    if amount < MIN_WITHDRAW: await update.message.reply_text(f"ন্যূনতম উইথড্র {fmt(MIN_WITHDRAW)}।"); return
    if amount > bal: await update.message.reply_text(f"পর্যাপ্ত ব্যালেন্স নেই: {fmt(bal)}"); return
    pay_id = " ".join(context.args[1:])
    with conn() as c:
        c.execute("UPDATE users SET balance=? WHERE id=?", (str(bal-amount),uid))
        c.execute("INSERT INTO withdrawals(user_id,amount,pay_id) VALUES(?,?,?)", (uid,str(amount),pay_id))
        wid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    await update.message.reply_text(f"রিকোয়েস্ট #{wid} জমা হয়েছে। পেমেন্ট পাঠানো হয়নি; অ্যাডমিন যাচাই করবেন।")
    if ADMIN_ID:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Paid (ম্যানুয়াল)", callback_data=f"wpaid_{wid}"),
                                    InlineKeyboardButton("↩️ Refund", callback_data=f"wrefund_{wid}")]])
        await context.bot.send_message(ADMIN_ID, f"উইথড্র #{wid}\\nUser: {uid}\\nAmount: {fmt(amount)}\\nPay ID: {pay_id}", reply_markup=kb)

async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not ADMIN_ID:
        await update.message.reply_text("শুধু অ্যাডমিনের জন্য।"); return
    parts = " ".join(context.args).split("|")
    if len(parts) != 3:
        await update.message.reply_text("ব্যবহার: /addtask শিরোনাম | https://example.com/video | 0.10"); return
    title,url,reward = [x.strip() for x in parts]
    try: amount = Decimal(reward)
    except InvalidOperation: await update.message.reply_text("রিওয়ার্ড সঠিক সংখ্যা হতে হবে।"); return
    if not url.startswith(("https://","http://")) or not amount.is_finite() or amount <= 0:
        await update.message.reply_text("সঠিক URL ও positive reward দিন।"); return
    with conn() as c: c.execute("INSERT INTO tasks(title,url,reward) VALUES(?,?,?)",(title,url,str(amount)))
    await update.message.reply_text("টাস্ক যোগ হয়েছে।")

async def withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID or not ADMIN_ID: await q.message.reply_text("শুধু অ্যাডমিনের জন্য।"); return
    action, raw=q.data.split("_",1); wid=int(raw)
    with conn() as c:
        w=c.execute("SELECT * FROM withdrawals WHERE id=?",(wid,)).fetchone()
        if not w or w["status"]!="pending": await q.message.reply_text("রিকোয়েস্ট আগেই প্রক্রিয়া করা হয়েছে।"); return
        if action=="wpaid":
            c.execute("UPDATE withdrawals SET status='paid' WHERE id=?",(wid,))
            msg="অ্যাডমিন রিকোয়েস্টটি Paid হিসেবে চিহ্নিত করেছেন। Binance লেনদেন আলাদাভাবে যাচাই করুন।"
        else:
            c.execute("UPDATE withdrawals SET status='refunded' WHERE id=?",(wid,))
            b=Decimal(c.execute("SELECT balance FROM users WHERE id=?",(w["user_id"],)).fetchone()[0])
            c.execute("UPDATE users SET balance=? WHERE id=?",(str(b+Decimal(w["amount"])),w["user_id"]))
            msg="উইথড্র রিকোয়েস্ট ফেরত দেওয়া হয়েছে; ব্যালেন্স পুনরুদ্ধার হয়েছে।"
    await context.bot.send_message(w["user_id"],msg); await q.message.reply_text("সম্পন্ন।")

def main():
    if not TOKEN: raise SystemExit("BOT_TOKEN environment variable সেট করুন।")
    init()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("withdraw",withdraw))
    app.add_handler(CommandHandler("addtask",addtask))
    app.add_handler(CallbackQueryHandler(withdraw_action, pattern=r"^w(paid|refund)_"))
    app.add_handler(CallbackQueryHandler(click))
    app.run_polling()

if __name__=="__main__": main()
