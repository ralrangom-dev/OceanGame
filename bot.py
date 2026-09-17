import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


BOT_TOKEN = os.getenv("BOT_TOKEN")


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("👤 پروفایل / موجودی", callback_data="profile"),
        ],
        [
            InlineKeyboardButton("🛒 فروشگاه", callback_data="shop"),
            InlineKeyboardButton("🏠 کسب درآمد", callback_data="income"),
        ],
        [
            InlineKeyboardButton("🏦 بانک", callback_data="bank"),
            InlineKeyboardButton("📈 ترید", callback_data="trade"),
        ],
        [
            InlineKeyboardButton("💱 صرافی رمزارز", callback_data="crypto"),
            InlineKeyboardButton("🏁 مسابقه/ماشین‌ها", callback_data="cars"),
        ],
        [
            InlineKeyboardButton("😎 بازار سیاه", callback_data="black_market"),
            InlineKeyboardButton("📦 انبار و فروش", callback_data="inventory"),
        ],
        [
            InlineKeyboardButton("🕸 دارک وب", callback_data="dark_web"),
        ],
        [
            InlineKeyboardButton("🏳️ کلن", callback_data="clan"),
        ],
        [
            InlineKeyboardButton("❓ راهنما", callback_data="help"),
        ],
        [
            InlineKeyboardButton("➕ افزودن ربات به گروه", callback_data="add_group"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        f"👋 سلام {user.first_name}\n\n"
        "💵 موجودی: 0 $\n"
        "🏦 بانک: 0 $\n"
        "⭐️ سطح: نوب\n\n"
        "از منوی زیر استفاده کن:"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "profile":
        text = "👤 پروفایل / موجودی\n\n💵 موجودی: 0 $\n🏦 بانک: 0 $\n⭐️ سطح: نوب"

    elif query.data == "shop":
        text = "🛒 فروشگاه\n\nفعلاً فروشگاه در حال ساخت است."

    elif query.data == "income":
        text = "🏠 کسب درآمد\n\nفعلاً این بخش در حال ساخت است."

    elif query.data == "bank":
        text = "🏦 بانک\n\nبرای استفاده از بانک در نسخه بعدی آماده می‌شود."

    elif query.data == "trade":
        text = "📈 ترید\n\nبخش ترید در حال ساخت است."

    elif query.data == "crypto":
        text = "💱 صرافی رمزارز\n\nبخش صرافی در حال ساخت است."

    elif query.data == "cars":
        text = "🏁 مسابقه/ماشین‌ها\n\nبخش ماشین‌ها و مسابقه در حال ساخت است."

    elif query.data == "black_market":
        text = "😎 بازار سیاه\n\nاین بخش در حال ساخت است."

    elif query.data == "inventory":
        text = "📦 انبار و فروش\n\nاین بخش در حال ساخت است."

    elif query.data == "dark_web":
        text = "🕸 دارک وب\n\nاین بخش در حال ساخت است."

    elif query.data == "clan":
        text = "🏳️ کلن\n\nاین بخش در حال ساخت است."

    elif query.data == "help":
        text = "❓ راهنما\n\nراهنمای کامل بازی به‌زودی اضافه می‌شود."

    elif query.data == "add_group":
        text = "➕ برای افزودن ربات به گروه، ربات را به گروه موردنظر اضافه کن."

    else:
        text = "این بخش هنوز ساخته نشده است."

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت به منو", callback_data="back")]
        ])
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    text = (
        f"👋 سلام {user.first_name}\n\n"
        "💵 موجودی: 0 $\n"
        "🏦 بانک: 0 $\n"
        "⭐️ سطح: نوب\n\n"
        "از منوی زیر استفاده کن:"
    )

    await query.edit_message_text(
        text,
        reply_markup=main_menu()
    )


def run():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("OceanGame started")
    app.run_polling()


if __name__ == "__main__":
    run()
