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
        text = (
            "🏠 کسب درآمد\n\n"
            "روی هر مورد بزن تا جزئیاتشو ببینی.\n"
            "درآمد جمع شده: 💵 0 $"
        )
        income_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏪 سوپرمارکت — +8,000/۵س", callback_data="income_supermarket")],
            [InlineKeyboardButton("🍽️ رستوران — +16,000/۵س", callback_data="income_restaurant")],
            [InlineKeyboardButton("🥖 نانوایی — +28,000/۵س", callback_data="income_bakery")],
            [InlineKeyboardButton("🌾 مزرعه آرد — +48,000/۵س", callback_data="income_flour_farm")],
            [InlineKeyboardButton("🏭 کارخانه — +74,000/۵س", callback_data="income_factory")],
            [InlineKeyboardButton("🚫 جنده‌خونه — +105,000/۵س", callback_data="income_brothel")],
            [InlineKeyboardButton("⛏️ معدن آهن — +150,000/۵س", callback_data="income_iron_mine")],
            [InlineKeyboardButton("⭐ مزرعه تریاک — +220,000/۵س", callback_data="income_opium_farm")],
            [InlineKeyboardButton("🥙 فلافلی — +300,000/۵س Ocean", callback_data="income_falafel")],
            [InlineKeyboardButton("🍗 اکبر جوجه — +420,000/۵س", callback_data="income_akbar_jojeh")],
            [InlineKeyboardButton("💰 برداشت درآمد (0)", callback_data="income_collect")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="home")],
        ])
        await q.edit_message_text(text, reply_markup=income_keyboard)
        return
    elif data.startswith("income_"):
        income_details = {
            "income_supermarket": ("🏪 سوپرمارکت", 8000),
            "income_restaurant": ("🍽️ رستوران", 16000),
            "income_bakery": ("🥖 نانوایی", 28000),
            "income_flour_farm": ("🌾 مزرعه آرد", 48000),
            "income_factory": ("🏭 کارخانه", 74000),
            "income_brothel": ("🚫 جنده‌خونه", 105000),
            "income_iron_mine": ("⛏️ معدن آهن", 150000),
            "income_opium_farm": ("⭐ مزرعه تریاک", 220000),
            "income_falafel": ("🥙 فلافلی", 300000),
            "income_akbar_jojeh": ("🍗 اکبر جوجه", 420000),
        }
        if data in income_details:
            name, amount = income_details[data]
            text = (
                f"{name}\n\n"
                f"💵 درآمد: +{amount:,} $ در هر ۵ ثانیه\n\n"
                "برای دیدن وضعیت کسب درآمد، به منوی کسب درآمد برگرد."
            )
        elif data == "income_collect":
            text = "💰 برداشت درآمد\n\nفعلاً درآمد قابل برداشت: 0 $"
        else:
            text = "❌ این گزینه پیدا نشد."
        await q.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به کسب درآمد", callback_data="income")]
            ])
        )
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
