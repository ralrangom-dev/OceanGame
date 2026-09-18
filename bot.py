import os
import sqlite3
import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "oceangame.db"


def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            coins INTEGER NOT NULL DEFAULT 0,
            bank INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_player(user):
    conn = db()
    row = conn.execute("SELECT * FROM players WHERE user_id=?", (user.id,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO players(user_id,name,coins,bank,level,created_at) VALUES(?,?,?,?,?,?)",
            (user.id, user.first_name or "بازیکن", 0, 0, 1, int(time.time())),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM players WHERE user_id=?", (user.id,)).fetchone()
    else:
        conn.execute("UPDATE players SET name=? WHERE user_id=?", (user.first_name or row["name"], user.id))
        conn.commit()
        row = conn.execute("SELECT * FROM players WHERE user_id=?", (user.id,)).fetchone()
    conn.close()
    return row


def B(text, callback_data, style="primary", url=None):
    kw={"text":text,"callback_data":callback_data}
    if url:
        kw={"text":text,"url":url}
    else:
        kw["style"]=style
    return InlineKeyboardButton(**kw)


def main_menu():
    return InlineKeyboardMarkup([
        [B("👤 پروفایل / موجودی", "profile")],
        [B("🏠 کسب درآمد", "income"), B("🏦 بانک", "bank")],
        [B("📈 ترید", "trade"), B("🏁 مسابقه / ماشین‌ها", "cars")],
        [B("💱 صرافی رمزارز", "crypto"), B("📦 انبار و فروش", "inventory")],
        [B("🛒 فروشگاه", "shop")],
        [B("🏴 بازار سیاه", "black_market"), B("🕸️ دارک وب", "dark_web")],
        [B("🏳️ کلن", "clan")],
        [B("❓ راهنما", "help")],
        [B("➕ افزودن ربات به گروه", "add_group")],
    ])


INCOME = {
    "supermarket": ("🏪 سوپرمارکت", 80000, 8000),
    "restaurant": ("🍽️ رستوران", 160000, 16000),
    "bakery": ("🥖 نانوایی", 280000, 28000),
    "flour_farm": ("🌾 مزرعه آرد", 480000, 48000),
    "factory": ("🏭 کارخانه", 740000, 74000),
    "brothel": ("🚫 جنده‌خونه", 1050000, 105000),
    "iron_mine": ("⛏️ معدن آهن", 1500000, 150000),
    "opium_farm": ("⭐ مزرعه تریاک", 2200000, 220000),
    "falafel": ("🥙 فلافلی", 3000000, 300000),
    "akbar_jojeh": ("🍗 اکبر جوجه", 4200000, 420000),
}

STORE = {
    "pet": [("🐶 سگ", "PET01", 5000),("🐱 گربه", "PET02", 7000),("🐰 خرگوش", "PET03", 9000)],
    "vehicle": [("🚘 خودروی فرار", "HT05", 20000),("🏍️ موتور فرار", "HT06", 30000)],
    "baby": [("🍼 شیشه شیر", "BABY01", 1500),("🧸 اسباب‌بازی", "BABY02", 2500),("👶 کالسکه", "BABY03", 12000)],
}

BLACK_MARKET = [("🔪 چاقو","W_KNIFE",2000),("🎭 نقاب خیابانی","BM002",2000),("🏍️ موتور فرار","HT06",2000),("🗡️ شمشیر چوبی","SW001",2000),("🧤 دستکش بی‌ردپا","MUG01",2000),("🎭 ماسک سرقت","HT01",3000),("🧪 معجون سلامتی","HT07",3200),("🛡️ زره چرمی","AR001",3200)]

CARS = {"پراید":80000,"پژو ۲۰۶":250000,"سمند":400000,"شاهین":800000,"BMW":2500000,"مرسدس بنز":4000000,"فراری":10000000,"بوگاتی":30000000}

CRYPTO = [("ADA","کاردانو",1.003),("BTC","بیتکوین",10410.243),("DOGE","دوج کوین",0.244),("ETH","اتریوم",1296.764),("GOLD","طلا",2038.289),("OCEAN","اوشن",22.835),("OIL","نفت",65.093),("PEPE","پپه",0.019),("SHIB","شیبا",0.004),("SILVER","نقره",25.014),("SOL","سولانا",121.334),("TON","تون کوین",4.477),("USDT","تتر",0.852),("XRP","ریپل",2.878)]

def home_text(user):
    p = get_player(user)
    return (f"👋 سلام {p['name']}\n\n"
            f"💲 موجودی: $ {p['coins']:,}\n"
            f"🏦 بانک: $ {p['bank']:,}\n"
            f"🏷️ سطح: نوب (لول {p['level']})\n\n"
            "از منوی زیر استفاده کن:")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(home_text(update.effective_user), reply_markup=main_menu())


def page_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت به منو", callback_data="home")]
    ])


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); data=q.data; user=q.from_user; p=get_player(user)
    if data=="home": return await q.edit_message_text(home_text(user), reply_markup=main_menu())
    if data=="profile":
        text=f"👤 {p['name']}\n💲 موجودی: $ {p['coins']:,}\n🏦 بانک: $ {p['bank']:,}\n💰 مجموع: $ {p['coins']+p['bank']:,}\n🏷️ سطح: نوب (لول {p['level']})"
        return await q.edit_message_text(text, reply_markup=page_keyboard())
    if data=="bank":
        text=f"🏦 بانک\n\n💲 موجودی: $ {p['coins']:,}\n🏦 بانک: $ {p['bank']:,}\n\nراهنما:\nسپرده + مبلغ\nمثال: سپرده 500"
        return await q.edit_message_text(text, reply_markup=page_keyboard())
    if data=="income":
        rows=[]
        for k,(n,price,inc) in INCOME.items(): rows.append([B(f"{n} — +{inc:,}/۵س",f"income_{k}","primary")])
        rows += [[B("💰 برداشت درآمد (0 $)","income_collect")],[B("🔙 برگشت","home")]]
        return await q.edit_message_text("🏠 کسب درآمد\n\nروی هر مورد بزن تا جزئیاتشو ببینی.\nدرآمد جمع شده: 💵 0 $", reply_markup=InlineKeyboardMarkup(rows))
    if data.startswith("income_"):
        key=data[7:]
        if key=="collect": return await q.edit_message_text("💰 برداشت درآمد\n\nفعلاً درآمد قابل برداشت: 0 $", reply_markup=InlineKeyboardMarkup([[B("🔙 برگشت به کسب درآمد","income")]]))
        n,price,inc=INCOME.get(key,("❌",0,0))
        text=f"{n}\n\n💵 قیمت خرید: {price:,} $\n💰 درآمد هر ۵ ساعت: {inc:,} $\n📦 ظرفیت: 1\n\nبرای خرید این کسب‌وکار دکمه زیر را بزن."
        return await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[B(f"🟢 خرید — {price:,} $",f"buy_income_{key}","success")],[B("🔙 برگشت","income")]]))
    if data.startswith("buy_income_"):
        key=data[11:]; n,price,inc=INCOME.get(key,("",0,0))
        if not price: return await q.edit_message_text("❌ گزینه نامعتبر است.",reply_markup=page_keyboard())
        if p['coins']<price: return await q.answer("❌ موجودی کافی نداری.",show_alert=True)
        conn=db(); conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?",(price,user.id)); conn.commit(); conn.close()
        return await q.edit_message_text(f"✅ {n} با موفقیت خریداری شد.\n💵 درآمد: {inc:,} $ در هر ۵ ساعت",reply_markup=InlineKeyboardMarkup([[B("🔙 برگشت به کسب درآمد","income")]]))
    if data=="shop":
        return await q.edit_message_text("🛒 فروشگاه\n\nچی میخوای بخری؟",reply_markup=InlineKeyboardMarkup([[B("🐾 پت","shop_pet")],[B("🚘 وسیله نقلیه","shop_vehicle")],[B("🍼 لوازم بچه","shop_baby")],[B("🔙 برگشت","home")]]))
    if data in ("shop_pet","shop_vehicle","shop_baby"):
        key=data[5:]; rows=[]
        for name,item,price in STORE[key]: rows.append([B(f"{name} — {price:,} $",f"buy_store_{key}_{item}","success")])
        rows.append([B("🔙 برگشت به فروشگاه","shop")])
        return await q.edit_message_text({"pet":"🐾 پت","vehicle":"🚘 وسیله نقلیه","baby":"🍼 لوازم بچه"}[key],reply_markup=InlineKeyboardMarkup(rows))
    if data.startswith("buy_store_"):
        _,_,key,item=data.split("_",3); found=next((x for x in STORE[key] if x[1]==item),None)
        if not found:return await q.answer("❌ آیتم پیدا نشد.",show_alert=True)
        name,item,price=found
        if p['coins']<price:return await q.answer("❌ موجودی کافی نداری.",show_alert=True)
        conn=db(); conn.execute("CREATE TABLE IF NOT EXISTS inventory(user_id INTEGER,item_id TEXT,item_name TEXT,quantity INTEGER,PRIMARY KEY(user_id,item_id))"); conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?",(price,user.id)); conn.execute("INSERT INTO inventory VALUES(?,?,?,1) ON CONFLICT(user_id,item_id) DO UPDATE SET quantity=quantity+1",(user.id,item,name)); conn.commit(); conn.close()
        return await q.answer("✅ خرید انجام شد و به انبار اضافه شد.",show_alert=True)
    if data=="cars":
        rows=[[B(f"🚗 خرید {n} — {v:,}",f"buy_car_{n}","success")] for n,v in CARS.items()]; rows.append([B("منو 🔙","home")])
        return await q.edit_message_text("🏁 ماشین‌ها و مسابقه\n\nماشین‌های تو:\n—\n\nبرای شروع مسابقه توی گروه بنویس: مسابقه 5000",reply_markup=InlineKeyboardMarkup(rows))
    if data.startswith("buy_car_"):
        n=data[9:]; price=CARS.get(n)
        if p['coins']<price:return await q.answer("❌ موجودی کافی نداری.",show_alert=True)
        conn=db(); conn.execute("CREATE TABLE IF NOT EXISTS cars(user_id INTEGER,car_name TEXT,price INTEGER,PRIMARY KEY(user_id,car_name))"); conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?",(price,user.id)); conn.execute("INSERT OR REPLACE INTO cars VALUES(?,?,?)",(user.id,n,price)); conn.commit(); conn.close(); return await q.answer("✅ ماشین خریداری شد.",show_alert=True)
    if data=="crypto":
        rows=[]
        for sym,name,price in CRYPTO: rows.append([B(f"💲 خرید {sym}",f"crypto_buy_{sym}","success"),B(f"💷 فروش {sym}",f"crypto_sell_{sym}")])
        rows.append([B("برگشت 🔙","home")]); text="💱 صرافی رمزارز\n\nبرای مقدار دلخواه بنویس: خرید 0.5 بیتکوین یا فروش OCEAN 12\n\n"+"\n".join(f"{s} ({n}) — {p}" for s,n,p in CRYPTO)
        return await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows))
    if data=="inventory":
        conn=db(); conn.execute("CREATE TABLE IF NOT EXISTS inventory(user_id INTEGER,item_id TEXT,item_name TEXT,quantity INTEGER,PRIMARY KEY(user_id,item_id))"); rows=conn.execute("SELECT item_id,item_name,quantity FROM inventory WHERE user_id=? AND quantity>0",(user.id,)).fetchall(); conn.close(); text="📦 انبار\n\n"+("\n".join(f"📦 {r['item_name']} [{r['item_id']}] × {r['quantity']}" for r in rows) if rows else "انبار خالی است.")+"\n\nفروش به ربات با نصف قیمت خرید: فروش <id>"; return await q.edit_message_text(text,reply_markup=page_keyboard())
    if data=="black_market":
        rows=[]
        for name,item,price in BLACK_MARKET: rows.append([B(f"{name} 💵 {price:,}",f"buy_black_{item}","danger" if item=="MUG01" else "primary")])
        rows.append([B("منو 🔙","home")]); return await q.edit_message_text("🏴 بازار سیاه — 64 آیتم\n\nبرای سرچ بنویس: سرچ شمشیر\nخرید با کد: SW001",reply_markup=InlineKeyboardMarkup(rows))
    if data.startswith("buy_black_"):
        item=data[10:]; found=next((x for x in BLACK_MARKET if x[1]==item),None)
        if not found:return await q.answer("❌ آیتم پیدا نشد.",show_alert=True)
        name,item,price=found
        if p['coins']<price:return await q.answer("❌ موجودی کافی نداری.",show_alert=True)
        conn=db(); conn.execute("CREATE TABLE IF NOT EXISTS inventory(user_id INTEGER,item_id TEXT,item_name TEXT,quantity INTEGER,PRIMARY KEY(user_id,item_id))"); conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?",(price,user.id)); conn.execute("INSERT INTO inventory VALUES(?,?,?,1) ON CONFLICT(user_id,item_id) DO UPDATE SET quantity=quantity+1",(user.id,item,name)); conn.commit(); conn.close(); return await q.answer("✅ خرید انجام شد.",show_alert=True)
    if data=="dark_web":
        text="دارک وب 🕸️\n\nبرای استفاده توی گروه روی پیام طرف ریپلای کن و بنویس:\n• اجیر قاتل — هزینه: $10,000 (از موجودی)\n• اجیر هکر — هزینه: $20,000 (از بانک)\n\nهر دو 30٪ شانس لو رفتن و جریمه دارن. اگه طرف بیمه باشه فقط 10٪ برداشت میشه."; return await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup([[B("منو 🔙","home")]]))
    if data=="clan":
        text="🏳️ راهنمای کلن\n\n• ساخت کلن <اسم> — $40,000\n• جوین <اسم کلن> — درخواست عضویت\n• کلن <اسم> — کارت کلن (رهبر/معاون: مدیریت اعضا و خزانه)\n• واریز کلن <مبلغ> / برداشت کلن <مبلغ>\n• چالش کلن — پله‌های امتیاز و جایزه‌ها\n• اعلام جنگ کلن <اسم کلن> — فقط رهبر/معاون\n• حمله / دفاع — هر ۲۵ دقیقه یک بار\n• رتبه کلن‌ها — جدول جهانی\n• خروج از کلن / انحلال کلن"; return await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup([[B("منو 🔙","home")]]))
    if data=="help":
        rows=[[B("🏳️ کلن","clan"),B("💲 درآمد رایگان","income")],[B("🎮 بازی‌ها","games"),B("💰 پول و بانک","bank")],[B("🏠 سرمایه‌گذاری","income"),B("🛒 فروشگاه و بازار","shop")],[B("💜 اجتماعی و خانواده","social"),B("🥷 دزدی و دارک وب","dark_web")],[B("🚀 موشک","rocket"),B("🏆 سایر","other")],[B("منو اصلی 🔙","home")]]; return await q.edit_message_text("💾 راهنمای ربات آقایون\n\nروی هر دسته بزن تا دستوراتش رو ببینی.",reply_markup=InlineKeyboardMarkup(rows))
    if data=="add_group":
        username=context.bot.username or "OceanGameeboBot"; return await q.edit_message_text("➕ افزودن ربات به گروه\n\nبرای اضافه کردن ربات به گروه روی دکمه زیر بزن.",reply_markup=InlineKeyboardMarkup([[B("➕ افزودن به گروه","add_group_link",url=f"https://t.me/{username}?startgroup=new")],[B("🔙 برگشت","home")]]))
    if data=="trade": text="📈 ترید\n\nبازار ترید OceanGame در حال ساخت است."
    elif data=="games": text="🎮 بازی‌ها\n\nبخش بازی‌ها در حال توسعه است."
    elif data=="social": text="💜 اجتماعی و خانواده\n\nبخش اجتماعی در حال توسعه است."
    elif data=="rocket": text="🚀 موشک\n\nبخش موشک در حال توسعه است."
    else: text="این بخش هنوز فعال نشده است."
    await q.edit_message_text(text,reply_markup=page_keyboard())


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user = update.effective_user

    if text in {"منو", "مانی", "/menu"}:
        await update.message.reply_text(home_text(user), reply_markup=main_menu())
        return

    if text == "موجودی":
        p = get_player(user)
        await update.message.reply_text(
            f"👤 {p['name']}\n"
            f"💲 موجودی: $ {p['coins']:,}\n"
            f"🏦 بانک: $ {p['bank']:,}\n"
            f"💰 مجموع: $ {p['coins'] + p['bank']:,}\n"
            f"🏷️ سطح: نوب (لول {p['level']})"
        )
        return

    if text.startswith("سپرده "):
        parts = text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await update.message.reply_text("❌ فرمت درست: سپرده + مبلغ\nمثال: سپرده 500")
            return
        amount = int(parts[1])
        if amount <= 0:
            await update.message.reply_text("❌ مبلغ باید بیشتر از صفر باشد.")
            return
        p = get_player(user)
        if p["coins"] < amount:
            await update.message.reply_text("❌ موجودی نقدی کافی نیست.")
            return
        conn = db()
        conn.execute("UPDATE players SET coins=coins-?, bank=bank+? WHERE user_id=?", (amount, amount, user.id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ {amount:,} $ به بانک منتقل شد.")
        return

    await update.message.reply_text(
        "دستور را نشناختم. برای دیدن منوی OceanGame بنویس: منو",
        reply_markup=main_menu()
    )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("OceanGame started")
    app.run_polling()


if __name__ == "__main__":
    main()
