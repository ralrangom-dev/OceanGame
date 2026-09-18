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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS income_businesses (
            user_id INTEGER NOT NULL,
            business_id TEXT NOT NULL,
            purchased_at INTEGER NOT NULL,
            last_collect INTEGER NOT NULL,
            PRIMARY KEY(user_id, business_id)
        )
    """)
    conn.commit()
    conn.close()


INCOME_BUSINESSES = {
    "supermarket": ("🏪 سوپرمارکت", 200000, 8000),
    "restaurant": ("🍽️ رستوران", 400000, 16000),
    "bakery": ("🥖 نانوایی", 700000, 28000),
    "flour_farm": ("🌾 مزرعه آرد", 1200000, 48000),
    "factory": ("🏭 کارخانه", 1800000, 74000),
    "brothel": ("🚫 جنده‌خونه", 2500000, 105000),
    "iron_mine": ("⛏️ معدن آهن", 3500000, 150000),
    "opium_farm": ("⭐ مزرعه تریاک", 5000000, 220000),
    "falafel": ("🥙 فلافلی Ocean", 7000000, 300000),
    "akbar_jojeh": ("🍗 اکبر جوجه", 13000000, 420000),
}


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


def business_ready(last_collect, amount):
    elapsed = max(0, int(time.time()) - int(last_collect))
    periods = elapsed // (5 * 60 * 60)
    return periods * amount


def income_ready(user_id):
    conn = db()
    rows = conn.execute("SELECT last_collect, business_id FROM income_businesses WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    total = 0
    for row in rows:
        amount = INCOME_BUSINESSES.get(row["business_id"], ("", 0, 0))[2]
        total += business_ready(row["last_collect"], amount)
    return total


def main_menu():
    # Inline buttons: Telegram controls their visual style.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 پروفایل / موجودی", callback_data="profile")],
        [
            InlineKeyboardButton("🏦 بانک", callback_data="bank"),
            InlineKeyboardButton("🏠 کسب درآمد", callback_data="income"),
        ],
        [
            InlineKeyboardButton("📈 ترید", callback_data="trade"),
            InlineKeyboardButton("🏁 مسابقه / ماشین‌ها", callback_data="cars"),
        ],
        [
            InlineKeyboardButton("💱 صرافی رمزارز", callback_data="crypto"),
            InlineKeyboardButton("📦 انبار و فروش", callback_data="inventory"),
        ],
        [
            InlineKeyboardButton("🛒 فروشگاه", callback_data="shop"),
            InlineKeyboardButton("🐾 پت و لوازم", callback_data="pets"),
        ],
        [
            InlineKeyboardButton("🏴 بازار سیاه", callback_data="black_market"),
            InlineKeyboardButton("🕸 دارک وب", callback_data="dark_web"),
        ],
        [InlineKeyboardButton("🏳️ کلن", callback_data="clan")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")],
        [InlineKeyboardButton("➕ افزودن ربات به گروه", callback_data="add_group")],
    ])


def home_text(user):
    p = get_player(user)
    return (
        f"👋 سلام {p['name']}\n\n"
        f"💲 موجودی: $ {p['coins']:,}\n"
        f"🏦 بانک: $ {p['bank']:,}\n"
        f"🏷️ سطح: نوب (لول {p['level']})\n\n"
        "🌊 به OceanGame خوش آمدی!"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(home_text(update.effective_user), reply_markup=main_menu())


def page_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت به منو", callback_data="home")]
    ])


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    user = q.from_user

    if data == "home":
        await q.edit_message_text(home_text(user), reply_markup=main_menu())
        return

    p = get_player(user)

    if data == "profile":
        text = (
            f"👤 {p['name']}\n\n"
            f"💲 موجودی: $ {p['coins']:,}\n"
            f"🏦 بانک: $ {p['bank']:,}\n"
            f"💰 مجموع: $ {p['coins'] + p['bank']:,}\n"
            f"🏷️ سطح: نوب (لول {p['level']})"
        )
    elif data == "bank":
        text = (
            "🏦 بانک\n\n"
            "راهنما:\n"
            "سپرده + مبلغ\n"
            "مثال: سپرده 500\n\n"
            f"💲 موجودی: $ {p['coins']:,}\n"
            f"🏦 بانک: $ {p['bank']:,}"
        )
    elif data == "income":
        conn = db()
        owned = conn.execute("SELECT business_id FROM income_businesses WHERE user_id=?", (user.id,)).fetchall()
        owned_ids = {r["business_id"] for r in owned}
        conn.close()
        total_ready = income_ready(user.id)
        text = (
            "🏠 کسب درآمد\n\n"
            "روی هر مورد بزن تا جزئیاتشو ببینی.\n"
            f"📦 تعداد شما: {len(owned_ids)} (ظرفیت ۹)\n"
            f"💰 قابل برداشت الان: $ {total_ready:,}"
        )
        rows = []
        for bid, (name, price, amount) in INCOME_BUSINESSES.items():
            mark = "✅" if bid in owned_ids else "🏢"
            rows.append([InlineKeyboardButton(f"{mark} {name}", callback_data=f"income_{bid}")])
        rows.append([InlineKeyboardButton(f"💰 برداشت درآمد ($ {total_ready:,})", callback_data="income_collect")])
        rows.append([InlineKeyboardButton("🔙 برگشت", callback_data="home")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
        return
    elif data.startswith("income_"):
        bid = data[len("income_"):]
        if bid in INCOME_BUSINESSES:
            name, price, amount = INCOME_BUSINESSES[bid]
            conn = db()
            owned = conn.execute(
                "SELECT * FROM income_businesses WHERE user_id=? AND business_id=?",
                (user.id, bid),
            ).fetchone()
            conn.close()
            if owned:
                ready = business_ready(owned["last_collect"], amount)
                count = 1
                text = (
                    f"{name}\n\n"
                    f"💵 قیمت خرید: $ {price:,}\n"
                    f"📈 درآمد پایه هر ۵ ساعت (هر واحد): $ {amount:,}\n"
                    f"📦 تعداد شما: {count} (ظرفیت ۹)\n"
                    f"🧮 مجموع درآمد واقعی: $ {ready:,}\n"
                    f"💰 قابل برداشت الان: $ {ready:,}"
                )
                buttons = [[InlineKeyboardButton(f"💰 برداشت ({ready:,})", callback_data="income_collect")]]
            else:
                text = (
                    f"{name}\n\n"
                    f"💵 قیمت خرید: $ {price:,}\n"
                    f"📈 درآمد پایه هر ۵ ساعت (هر واحد): $ {amount:,}\n"
                    "📦 تعداد شما: 0 (ظرفیت ۹)\n"
                    "🧮 مجموع درآمد واقعی: $ 0\n"
                    "💰 قابل برداشت الان: $ 0"
                )
                buttons = [[InlineKeyboardButton(f"🛒 خرید ({price:,})", callback_data=f"income_buy_{bid}")]]
            buttons.append([InlineKeyboardButton("🔙 برگشت", callback_data="income")])
            await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            return
        if bid == "collect":
            amount = income_ready(user.id)
            if amount <= 0:
                text = "💰 برداشت درآمد\n\n❌ فعلاً درآمد قابل برداشت ندارید."
            else:
                conn = db()
                conn.execute("UPDATE players SET coins=coins+? WHERE user_id=?", (amount, user.id))
                now = int(time.time())
                conn.execute("UPDATE income_businesses SET last_collect=? WHERE user_id=?", (now, user.id))
                conn.commit()
                conn.close()
                text = f"✅ مبلغ $ {amount:,} به موجودی شما اضافه شد."
            await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت به کسب درآمد", callback_data="income")]]))
            return
        if bid.startswith("buy_"):
            buy_id = bid[4:]
            if buy_id not in INCOME_BUSINESSES:
                await q.edit_message_text("❌ این کسب‌وکار پیدا نشد.", reply_markup=page_keyboard())
                return
            name, price, amount = INCOME_BUSINESSES[buy_id]
            conn = db()
            count = conn.execute("SELECT COUNT(*) AS c FROM income_businesses WHERE user_id=?", (user.id,)).fetchone()["c"]
            pnow = conn.execute("SELECT coins FROM players WHERE user_id=?", (user.id,)).fetchone()
            already = conn.execute("SELECT 1 FROM income_businesses WHERE user_id=? AND business_id=?", (user.id, buy_id)).fetchone()
            if already:
                result = "❌ این کسب‌وکار را قبلاً خریده‌ای."
            elif count >= 9:
                result = "❌ ظرفیت کسب‌وکارهای شما پر است. (۹ از ۹)"
            elif not pnow or pnow["coins"] < price:
                result = f"❌ موجودی کافی نیست. قیمت خرید: $ {price:,}"
            else:
                now = int(time.time())
                conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?", (price, user.id))
                conn.execute("INSERT INTO income_businesses(user_id,business_id,purchased_at,last_collect) VALUES(?,?,?,?)", (user.id, buy_id, now, now))
                conn.commit()
                result = f"✅ {name} با قیمت $ {price:,} خریداری شد."
            conn.close()
            await q.edit_message_text(result, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت به کسب درآمد", callback_data="income")]]))
            return
    elif data == "trade":
        text = "📈 ترید\n\nبازار ترید OceanGame در حال ساخت است."
    elif data == "cars":
        text = "🏁 مسابقه / ماشین‌ها\n\nخرید ماشین و مسابقه در این بخش قرار می‌گیرد."
    elif data == "crypto":
        text = "💱 صرافی رمزارز\n\nخرید و فروش ارزهای داخل بازی در این بخش قرار می‌گیرد."
    elif data == "inventory":
        text = "📦 انبار و فروش\n\nدارایی‌ها و فروش آیتم‌ها در این بخش قرار می‌گیرد."
    elif data == "shop":
        text = "🛒 فروشگاه\n\nچی میخوای بخری؟"
        shop_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🐾 پت", callback_data="shop_pet")],
            [InlineKeyboardButton("🚘 وسیله نقلیه", callback_data="shop_vehicle")],
            [InlineKeyboardButton("🍼 لوازم بچه", callback_data="shop_baby")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="home")],
        ])
        await q.edit_message_text(text, reply_markup=shop_keyboard)
        return
    elif data in ("shop_pet", "shop_vehicle", "shop_baby"):
        titles = {
            "shop_pet": "🐾 پت",
            "shop_vehicle": "🚘 وسیله نقلیه",
            "shop_baby": "🍼 لوازم بچه",
        }
        text = f"{titles[data]}\n\nاین بخش در مرحله بعد تکمیل می‌شود."
        await q.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به فروشگاه", callback_data="shop")]
            ])
        )
        return
    elif data == "pets":
        text = "🐾 پت و لوازم\n\nپت‌ها و لوازم جانبی در این بخش قرار می‌گیرند."
    elif data == "black_market":
        text = "🏴 بازار سیاه\n\nبخش بازار سیاه بازی در حال ساخت است."
    elif data == "dark_web":
        text = "🕸 دارک وب\n\nبخش دارک وب بازی در حال ساخت است."
    elif data == "clan":
        text = "🏳️ کلن\n\nبخش کلن و امکانات گروهی در حال ساخت است."
    elif data == "help":
        text = (
            "❓ راهنمای OceanGame\n\n"
            "منو\n"
            "موجودی\n"
            "سپرده 500\n\n"
            "دستورهای بیشتر با اضافه‌شدن بخش‌های بازی فعال می‌شوند."
        )
    elif data == "add_group":
        text = "➕ برای افزودن OceanGame به گروه، ربات را به گروه موردنظر اضافه کن."
    else:
        text = "این بخش هنوز فعال نشده است."

    await q.edit_message_text(text, reply_markup=page_keyboard())


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
