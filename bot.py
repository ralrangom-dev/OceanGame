import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        f"👋 سلام {user.first_name}\n\n"
        "💵 موجودی: 0 $\n"
        "🏦 بانک: 0 $\n"
        "⭐️ سطح: نوب\n\n"
        "🎮 به OceanGame خوش آمدی!"
    )

    await update.message.reply_text(text)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("OceanGame started")
    app.run_polling()


if __name__ == "__main__":
    main()
