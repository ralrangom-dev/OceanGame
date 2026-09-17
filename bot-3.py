import os
import random
import sqlite3
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters

DB_FILE = "kingdom.db"

# -------------------- DATABASE --------------------

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        coins INTEGER DEFAULT 10000,
        level INTEGER DEFAULT 1,
        health INTEGER DEFAULT 100,
        power INTEGER DEFAULT 100,
        defense INTEGER DEFAULT 100,
        army INTEGER DEFAULT 0,
        captured INTEGER DEFAULT 0,
        last_hunt INTEGER DEFAULT 0,
        safe_coins INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS crypto (
        symbol TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price INTEGER NOT NULL
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS crypto_holdings (
        user_id INTEGER,
        symbol TEXT,
        amount REAL DEFAULT 0,
        PRIMARY KEY (user_id, symbol)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS ingredients (
        name TEXT PRIMARY KEY,
        emoji TEXT,
        price INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER,
        ingredient TEXT,
        amount INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, ingredient)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY,
        name TEXT,
        emoji TEXT,
        time_seconds INTEGER,
        sell_price INTEGER,
        ingredients TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS cooking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        recipe_id INTEGER,
        started_at INTEGER,
        ready_at INTEGER,
        quantity INTEGER DEFAULT 1,
        claimed INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS fantasy_products (
        id INTEGER PRIMARY KEY,
        name TEXT,
        emoji TEXT,
        cost INTEGER,
        time_seconds INTEGER,
        sell_price INTEGER,
        risk INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS production (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        started_at INTEGER,
        ready_at INTEGER,
        quantity INTEGER DEFAULT 1,
        claimed INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        created_at INTEGER,
        resolved INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS kitchen_stats (
        user_id INTEGER PRIMARY KEY,
        level INTEGER DEFAULT 1,
        chef_level INTEGER DEFAULT 1,
        storage_level INTEGER DEFAULT 1
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS daily_activity (
        user_id INTEGER,
        day TEXT,
        cooked INTEGER DEFAULT 0,
        sold INTEGER DEFAULT 0,
        revenue INTEGER DEFAULT 0,
        mission_claimed INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, day)
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS customer_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        recipe_id INTEGER,
        quantity INTEGER,
        reward INTEGER,
        created_at INTEGER,
        expires_at INTEGER,
        claimed INTEGER DEFAULT 0
    )
    """)

    seed_data(conn)
    conn.commit()
    conn.close()


def seed_data(conn):
    crypto = [
        ("BTC", "Bitcoin", 100000),
        ("ETH", "Ethereum", 3500),
        ("USDT", "Tether", 1),
        ("BNB", "BNB", 650),
        ("XRP", "XRP", 2),
        ("SOL", "Solana", 200),
        ("USDC", "USD Coin", 1),
        ("DOGE", "Dogecoin", 0),
        ("TRX", "TRON", 0),
        ("ADA", "Cardano", 1),
    ]

    for symbol, name, price in crypto:
        conn.execute(
            "INSERT OR IGNORE INTO crypto(symbol,name,price) VALUES(?,?,?)",
            (symbol, name, price),
        )

    ingredients = [
        ("egg", "🥚", 30),
        ("bread", "🍞", 50),
        ("meat", "🥩", 150),
        ("cheese", "🧀", 80),
        ("tomato", "🍅", 40),
        ("chicken", "🍗", 180),
        ("flour", "🌾", 60),
        ("pasta", "🍝", 100),
        ("corn", "🌽", 70),
        ("fish", "🐟", 250),
        ("rice", "🍚", 90),
        ("chocolate", "🍫", 120),
    ]

    for name, emoji, price in ingredients:
        conn.execute(
            "INSERT OR IGNORE INTO ingredients(name,emoji,price) VALUES(?,?,?)",
            (name, emoji, price),
        )

    recipes = [
        (1, "نیمرو", "🍳", 60, 180, "egg:2"),
        (2, "همبرگر", "🍔", 180, 500, "meat:1,bread:1"),
        (3, "پیتزا", "🍕", 300, 900, "bread:1,cheese:2,tomato:2"),
        (4, "مرغ سوخاری", "🍗", 420, 1300, "chicken:2,flour:1"),
        (5, "پاستا", "🍝", 600, 1800, "pasta:1,tomato:2,cheese:1"),
        (6, "تاکو", "🌮", 720, 2200, "meat:1,corn:2,tomato:1"),
        (7, "سوشی", "🍣", 900, 3000, "fish:2,rice:2"),
        (8, "کیک", "🍰", 1200, 4500, "flour:2,egg:2,chocolate:1"),
    ]

    for recipe in recipes:
        conn.execute("""
        INSERT OR IGNORE INTO recipes
        (id,name,emoji,time_seconds,sell_price,ingredients)
        VALUES(?,?,?,?,?,?)
        """, recipe)

    # محصولات کاملاً خیالی و فانتزی؛ بدون دستور یا مواد ساخت واقعی
    products = [
        (1, "کریستال X", "🧪", 20000, 7200, 35000, 20),
        (2, "نئوکریستال", "🔮", 50000, 14400, 95000, 35),
        (3, "ماده Z", "⚗️", 100000, 28800, 220000, 50),
        (4, "امپراتور X", "💠", 250000, 43200, 600000, 70),
        (5, "هسته سیاه", "🧿", 500000, 86400, 1300000, 90),
    ]

    for product in products:
        conn.execute("""
        INSERT OR IGNORE INTO fantasy_products
        (id,name,emoji,cost,time_seconds,sell_price,risk)
        VALUES(?,?,?,?,?,?,?)
        """, product)


def get_player(user):
    conn = db()
    row = conn.execute(
        "SELECT * FROM players WHERE user_id=?",
        (user.id,),
    ).fetchone()

    if row is None:
        conn.execute("""
        INSERT INTO players
        (user_id,username,first_name,coins,level,health,power,defense,army,captured,last_hunt,safe_coins)
        VALUES(?,?,?,10000,1,100,100,100,0,0,0,0)
        """, (user.id, user.username, user.first_name))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM players WHERE user_id=?",
            (user.id,),
        ).fetchone()
    else:
        conn.execute(
            "UPDATE players SET username=?, first_name=? WHERE user_id=?",
            (user.username, user.first_name, user.id),
        )
        conn.commit()

    conn.close()
    return row


# -------------------- MENUS --------------------

def back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data="kingdom")]
    ])


def kingdom_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 پروفایل", callback_data="profile"), InlineKeyboardButton("📈 بازار ارز", callback_data="crypto")],
        [InlineKeyboardButton("🏦 بانک", callback_data="safe"), InlineKeyboardButton("🍳 آشپزخانه", callback_data="kitchen")],
        [InlineKeyboardButton("🏪 ارتقای آشپزخانه", callback_data="kitchen_upgrade"), InlineKeyboardButton("🎰 قمار", callback_data="gamble")],
    ])


def kingdom_text(player):
    return (
        f"👋 سلام {player['first_name']}\n\n"
        f"💵 | {player['coins']:,} $\n"
        f"🏦 | {player['safe_coins']:,} $\n"
        f"⭐️ | {player['level']}\n"
        f"❤️ | {player['health']}\n"
        f"⚔️ | {player['power']}\n"
        f"🛡 | {player['defense']}\n\n"
        "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        "گزینه موردنظر را انتخاب کن:"
    )


async def show_kingdom(update, context):
    player = get_player(update.effective_user)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            kingdom_text(player),
            reply_markup=kingdom_keyboard(),
        )
    else:
        await update.message.reply_text(
            kingdom_text(player),
            reply_markup=kingdom_keyboard(),
        )


# -------------------- PROFILE --------------------

async def profile(update, context):
    q = update.callback_query
    p = get_player(update.effective_user)

    username = f"@{p['username']}" if p["username"] else "بدون یوزرنیم"

    text = (
        "👤 پروفایل\n\n"
        f"👤 نام: {p['first_name']}\n"
        f"🔗 یوزرنیم: {username}\n"
        f"💵 $: {p['coins']:,}\n"
        f"⭐️ سطح: {p['level']}\n"
        f"❤️ سلامتی: {p['health']}\n"
        f"⚔️ قدرت: {p['power']}\n"
        f"🛡 دفاع: {p['defense']}\n"
    )

    await q.edit_message_text(text, reply_markup=back())


# -------------------- HUNT --------------------

async def hunt(update, context):
    user = update.effective_user
    get_player(user)
    now = int(time.time())

    conn = db()
    row = conn.execute(
        "SELECT coins,last_hunt FROM players WHERE user_id=?",
        (user.id,),
    ).fetchone()

    remaining = 300 - (now - row["last_hunt"])

    if remaining > 0:
        conn.close()
        await update.message.reply_text(
            f"⏳ خایمالی هنوز آماده نیست.\n"
            f"زمان باقی‌مانده: {remaining//60} دقیقه و {remaining%60} ثانیه"
        )
        return

    conn.execute(
        "UPDATE players SET coins=coins+100,last_hunt=? WHERE user_id=?",
        (now, user.id),
    )
    conn.commit()
    balance = conn.execute(
        "SELECT coins FROM players WHERE user_id=?",
        (user.id,),
    ).fetchone()["coins"]
    conn.close()

    await update.message.reply_text(
        f"🏹 خایمالی موفق!\n💰 +100 $\n💳 موجودی: {balance:,}\n"
        "⏱ خایمالی بعدی: ۵ دقیقه"
    )


# -------------------- TRANSFER / RIP --------------------

async def transfer(update, context):
    m = update.message

    if not m.reply_to_message:
        await m.reply_text("❌ روی پیام بازیکن Reply کن و بنویس: اهدای باج 1000")
        return

    parts = m.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await m.reply_text("❌ فرمت صحیح: اهدای باج 1000")
        return

    amount = int(parts[1])
    sender = m.from_user
    target = m.reply_to_message.from_user

    if amount <= 0:
        await m.reply_text("❌ مبلغ باید بیشتر از صفر باشد.")
        return

    if sender.id == target.id:
        await m.reply_text("❌ انتقال به خودت ممکن نیست.")
        return

    get_player(sender)
    get_player(target)

    conn = db()
    try:
        conn.execute("BEGIN IMMEDIATE")

        s = conn.execute(
            "SELECT coins FROM players WHERE user_id=?",
            (sender.id,),
        ).fetchone()

        if s["coins"] < amount:
            conn.rollback()
            await m.reply_text("❌ موجودی کافی نیست.")
            return

        conn.execute(
            "UPDATE players SET coins=coins-? WHERE user_id=?",
            (amount, sender.id),
        )
        conn.execute(
            "UPDATE players SET coins=coins+? WHERE user_id=?",
            (amount, target.id),
        )
        conn.commit()
    finally:
        conn.close()

    await m.reply_text(
        f"✅ انتقال انجام شد.\n💸 {amount:,} $ → {target.first_name}"
    )


async def rip(update, context):
    m = update.message

    if not m.reply_to_message:
        await m.reply_text("❌ روی پیام بازیکن Reply کن و بنویس: خفت گیری")
        return

    attacker = m.from_user
    target = m.reply_to_message.from_user

    if attacker.id == target.id:
        await m.reply_text("❌ نمی‌توانی خودت را هدف بگیری.")
        return

    get_player(attacker)
    get_player(target)

    conn = db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        a = conn.execute(
            "SELECT coins FROM players WHERE user_id=?",
            (attacker.id,),
        ).fetchone()["coins"]
        t = conn.execute(
            "SELECT coins FROM players WHERE user_id=?",
            (target.id,),
        ).fetchone()["coins"]

        if random.random() < 0.70:
            amount = int(t * 0.15)
            conn.execute(
                "UPDATE players SET coins=coins-? WHERE user_id=?",
                (amount, target.id),
            )
            conn.execute(
                "UPDATE players SET coins=coins+? WHERE user_id=?",
                (amount, attacker.id),
            )
            text = f"😈 موفق شدی!\n💰 {amount:,} $ گرفتی."
        else:
            amount = int(a * 0.07)
            conn.execute(
                "UPDATE players SET coins=coins-? WHERE user_id=?",
                (amount, attacker.id),
            )
            conn.execute(
                "UPDATE players SET coins=coins+? WHERE user_id=?",
                (amount, target.id),
            )
            text = f"💀 شکست خوردی!\n💸 {amount:,} $ از دست دادی."

        conn.commit()
    finally:
        conn.close()

    await m.reply_text(text)


# -------------------- CRYPTO MARKET --------------------

def crypto_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 مشاهده ارزها", callback_data="crypto_list")],
        [InlineKeyboardButton("💼 دارایی من", callback_data="crypto_wallet")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="kingdom")],
    ])


async def crypto_page(update, context):
    await update.callback_query.edit_message_text(
        "📈 بازار ارز دیجیتال\n\n"
        "ارزهای واقعی در بازی شبیه‌سازی شده‌اند و خریدها با $ بازی انجام می‌شود.\n\n"
        "برای خرید/فروش از دستورهای زیر استفاده کن:\n"
        "خرید BTC 2\n"
        "فروش BTC 1",
        reply_markup=crypto_menu(),
    )


async def crypto_list(update, context):
    conn = db()
    rows = conn.execute(
        "SELECT symbol,name,price FROM crypto ORDER BY price DESC"
    ).fetchall()
    conn.close()

    text = "📈 بازار ارز دیجیتال\n\n"
    for r in rows:
        price = r["price"]
        text += f"🪙 {r['name']} ({r['symbol']})\n💰 {price:,} $\n\n"

    text += "برای خرید: خرید BTC 1\nبرای فروش: فروش BTC 1"

    await update.callback_query.edit_message_text(
        text,
        reply_markup=back_crypto(),
    )


def back_crypto():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data="crypto")]
    ])


async def crypto_wallet(update, context):
    user = update.effective_user
    get_player(user)

    conn = db()
    rows = conn.execute("""
        SELECT h.symbol,h.amount,c.name,c.price
        FROM crypto_holdings h
        JOIN crypto c ON c.symbol=h.symbol
        WHERE h.user_id=? AND h.amount>0
    """, (user.id,)).fetchall()
    conn.close()

    if not rows:
        text = "💼 دارایی ارز دیجیتال\n\nهنوز ارزی نداری."
    else:
        text = "💼 دارایی ارز دیجیتال\n\n"
        for r in rows:
            text += (
                f"🪙 {r['name']} ({r['symbol']})\n"
                f"📦 مقدار: {r['amount']:g}\n"
                f"💰 ارزش تقریبی: {int(r['amount']*r['price']):,}\n\n"
            )

    await update.callback_query.edit_message_text(
        text,
        reply_markup=back_crypto(),
    )


async def crypto_trade(update, buy):
    m = update.message
    parts = m.text.split()

    if len(parts) != 3:
        await m.reply_text(
            "❌ مثال:\nخرید BTC 2\nفروش BTC 1"
        )
        return

    symbol = parts[1].upper()

    try:
        amount = float(parts[2])
    except ValueError:
        await m.reply_text("❌ مقدار باید عدد باشد.")
        return

    if amount <= 0:
        await m.reply_text("❌ مقدار باید بیشتر از صفر باشد.")
        return

    user = m.from_user
    get_player(user)

    conn = db()

    coin = conn.execute(
        "SELECT name,price FROM crypto WHERE symbol=?",
        (symbol,),
    ).fetchone()

    if not coin:
        conn.close()
        await m.reply_text("❌ این ارز در بازار بازی وجود ندارد.")
        return

    value = int(coin["price"] * amount)

    try:
        conn.execute("BEGIN IMMEDIATE")

        p = conn.execute(
            "SELECT coins FROM players WHERE user_id=?",
            (user.id,),
        ).fetchone()

        holding = conn.execute(
            "SELECT amount FROM crypto_holdings WHERE user_id=? AND symbol=?",
            (user.id, symbol),
        ).fetchone()

        current = holding["amount"] if holding else 0

        if buy:
            if p["coins"] < value:
                conn.rollback()
                await m.reply_text("❌ $ کافی نیست.")
                return

            conn.execute(
                "UPDATE players SET coins=coins-? WHERE user_id=?",
                (value, user.id),
            )

            conn.execute("""
                INSERT INTO crypto_holdings(user_id,symbol,amount)
                VALUES(?,?,?)
                ON CONFLICT(user_id,symbol)
                DO UPDATE SET amount=amount+excluded.amount
            """, (user.id, symbol, amount))

            text = (
                f"✅ خرید انجام شد.\n"
                f"🪙 {symbol}: {amount:g}\n"
                f"💸 هزینه: {value:,} $"
            )

        else:
            if current < amount:
                conn.rollback()
                await m.reply_text("❌ این مقدار ارز را نداری.")
                return

            conn.execute(
                "UPDATE players SET coins=coins+? WHERE user_id=?",
                (value, user.id),
            )
            conn.execute(
                "UPDATE crypto_holdings SET amount=amount-? "
                "WHERE user_id=? AND symbol=?",
                (amount, user.id, symbol),
            )

            text = (
                f"✅ فروش انجام شد.\n"
                f"🪙 {symbol}: {amount:g}\n"
                f"💰 دریافتی: {value:,} $"
            )

        conn.commit()
    finally:
        conn.close()

    await m.reply_text(text)


# Persian names shown to players; database keys remain stable English codes.
INGREDIENT_DISPLAY = {
    "egg": "تخمه مرغ",
    "bread": "نان",
    "meat": "گوشت",
    "cheese": "پنیر",
    "tomato": "گوجه",
    "chicken": "مرغ",
    "flour": "آرد",
    "pasta": "پاستا",
    "corn": "ذرت",
    "fish": "ماهی",
    "rice": "برنج",
    "chocolate": "شکلات",
}
INGREDIENT_ALIASES = {v: k for k, v in INGREDIENT_DISPLAY.items()}
RECIPE_ALIASES = {}

# -------------------- KITCHEN --------------------

def kitchen_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 خرید مواد اولیه", callback_data="ingredients")],
        [InlineKeyboardButton("🍳 منوی غذاها", callback_data="recipes")],
        [InlineKeyboardButton("🔥 وضعیت پخت", callback_data="cooking")],
        [InlineKeyboardButton("📦 غذاهای آماده / فروش", callback_data="food_sell")],
        [InlineKeyboardButton("📋 سفارش مشتری", callback_data="orders")],
        [InlineKeyboardButton("🏪 ارتقای آشپزخانه", callback_data="kitchen_upgrade")],
        [InlineKeyboardButton("🧑‍🍳 آشپزها", callback_data="chefs")],
        [InlineKeyboardButton("📦 انبار مواد", callback_data="kitchen_inventory")],
        [InlineKeyboardButton("🎯 ماموریت روزانه", callback_data="daily_mission")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="kingdom")],
    ])


def kitchen_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 آشپزخانه", callback_data="kitchen")]])


def kitchen_stats(user_id):
    conn=db(); row=conn.execute("SELECT * FROM kitchen_stats WHERE user_id=?",(user_id,)).fetchone()
    if not row:
        conn.execute("INSERT INTO kitchen_stats(user_id) VALUES(?)",(user_id,)); conn.commit(); row=conn.execute("SELECT * FROM kitchen_stats WHERE user_id=?",(user_id,)).fetchone()
    conn.close(); return row


def ingredient_market_price(name, base):
    day=time.strftime("%Y-%m-%d")
    seed=sum(ord(c) for c in name+day)
    return max(1, int(round(base*(0.90+(seed%21)/100))))


def storage_capacity(level):
    return 30 + (level-1)*20


def cooking_capacity(level):
    return 5 + (level-1)


def chef_speed(level):
    return max(0.60, 1.0-(level-1)*0.05)


def ensure_daily(user_id):
    day=time.strftime("%Y-%m-%d"); conn=db(); conn.execute("INSERT OR IGNORE INTO daily_activity(user_id,day) VALUES(?,?)",(user_id,day)); conn.commit(); row=conn.execute("SELECT * FROM daily_activity WHERE user_id=? AND day=?",(user_id,day)).fetchone(); conn.close(); return row


async def kitchen(update, context):
    user=update.effective_user; get_player(user); ks=kitchen_stats(user.id); conn=db(); active=conn.execute("SELECT COUNT(*) AS n FROM cooking WHERE user_id=? AND claimed=0",(user.id,)).fetchone()['n']; ready=conn.execute("SELECT COUNT(*) AS n FROM cooking WHERE user_id=? AND claimed=0 AND ready_at<=?",(user.id,int(time.time()))).fetchone()['n']; coins=conn.execute("SELECT coins FROM players WHERE user_id=?",(user.id,)).fetchone()['coins']; conn.close()
    cap=cooking_capacity(ks['level'])
    text=(f"👨‍🍳 آشپزخانه\n\n💵 موجودی: {coins:,} $\n🏪 سطح آشپزخانه: {ks['level']}\n🧑‍🍳 سطح آشپز: {ks['chef_level']}\n📦 ظرفیت انبار: {storage_capacity(ks['storage_level'])}\n🔥 ظرفیت پخت: {active}/{cap}\n🍳 در حال پخت: {active-ready}\n✅ آماده فروش: {ready}\n\n🛒 مواد بخر → 🍳 بپز → 📋 سفارش مشتری → 💵 بفروش")
    if update.callback_query: await update.callback_query.edit_message_text(text,reply_markup=kitchen_menu())
    else: await update.message.reply_text(text,reply_markup=kitchen_menu())


async def ingredients_page(update, context):
    user=update.effective_user; get_player(user); conn=db(); rows=conn.execute("SELECT i.name,i.emoji,i.price,COALESCE(inv.amount,0) AS amount FROM ingredients i LEFT JOIN inventory inv ON inv.ingredient=i.name AND inv.user_id=? ORDER BY i.price",(user.id,)).fetchall(); conn.close()
    table=["🛒 فروشگاه مواد غذایی","","مواد اولیه     قیمت     موجودی","────────────────────────"]
    for r in rows:
        display=INGREDIENT_DISPLAY.get(r['name'],r['name']); price=ingredient_market_price(r['name'],r['price']); table.append(f"{r['emoji']} {display:<8} {price:>5,}$      {r['amount']:>3}")
    table += ["────────────────────────","","⌨️ خرید تخمه مرغ 5","مثال: خرید گوشت 2"]
    await update.callback_query.edit_message_text("\n".join(table),reply_markup=kitchen_back())


async def kitchen_inventory_page(update, context):
    user=update.effective_user; get_player(user); ks=kitchen_stats(user.id); conn=db(); rows=conn.execute("SELECT i.name,i.emoji,COALESCE(inv.amount,0) AS amount FROM ingredients i LEFT JOIN inventory inv ON inv.ingredient=i.name AND inv.user_id=? ORDER BY i.price",(user.id,)).fetchall(); conn.close(); total=sum(r['amount'] for r in rows); cap=storage_capacity(ks['storage_level'])
    text=f"📦 انبار مواد\n\nظرفیت: {total}/{cap}\n\n"+"\n".join(f"{r['emoji']} {INGREDIENT_DISPLAY.get(r['name'],r['name'])}: {r['amount']}" for r in rows)
    if update.callback_query: await update.callback_query.edit_message_text(text,reply_markup=kitchen_back())
    else: await update.message.reply_text(text,reply_markup=kitchen_back())


def back_kitchen(): return kitchen_back()


async def buy_ingredient(update, context):
    m = update.message
    parts = m.text.split()
    if len(parts) < 3 or not parts[-1].isdigit():
        await m.reply_text("❌ دستور صحیح: خرید تخمه مرغ 5")
        return
    display_name = " ".join(parts[1:-1]).strip()
    name = INGREDIENT_ALIASES.get(display_name)
    amount = int(parts[-1])
    if not name:
        await m.reply_text("❌ نام ماده غذایی نامعتبر است. از منوی خرید مواد غذایی استفاده کن.")
        return
    if amount <= 0 or amount > 1000:
        await m.reply_text("❌ مقدار باید بین 1 تا 1000 باشد.")
        return
    user = m.from_user
    get_player(user)
    conn = db()
    try:
        ingredient = conn.execute("SELECT emoji,price FROM ingredients WHERE name=?", (name,)).fetchone()
        if not ingredient:
            await m.reply_text("❌ این ماده غذایی وجود ندارد.")
            return
        market_price = ingredient_market_price(name, ingredient["price"])
        ks = kitchen_stats(user.id)
        conn0 = db()
        current = conn0.execute("SELECT COALESCE(SUM(amount),0) AS n FROM inventory WHERE user_id=?", (user.id,)).fetchone()["n"]
        conn0.close()
        if current + amount > storage_capacity(ks["storage_level"]):
            await m.reply_text(f"❌ انبار جا ندارد.\n📦 ظرفیت: {storage_capacity(ks["storage_level"])}")
            return
        cost = market_price * amount
        conn.execute("BEGIN IMMEDIATE")
        p = conn.execute("SELECT coins FROM players WHERE user_id=?", (user.id,)).fetchone()
        if p["coins"] < cost:
            conn.rollback()
            await m.reply_text(f"❌ $ کافی نیست.\n💵 $ موردنیاز: {cost:,}\n💳 موجودی: {p['coins']:,}")
            return
        conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?", (cost,user.id))
        conn.execute("""INSERT INTO inventory(user_id,ingredient,amount) VALUES(?,?,?)
            ON CONFLICT(user_id,ingredient) DO UPDATE SET amount=amount+excluded.amount""", (user.id,name,amount))
        conn.commit()
        new_balance = p["coins"] - cost
        new_stock = conn.execute("SELECT amount FROM inventory WHERE user_id=? AND ingredient=?", (user.id,name)).fetchone()["amount"]
    finally:
        conn.close()
    await m.reply_text(f"✅ خرید موفق\n{ingredient['emoji']} {INGREDIENT_DISPLAY[name]} ×{amount}\n💸 هزینه: {cost:,} $\n💵 موجودی $: {new_balance:,}\n📦 موجودی ماده: {new_stock}")


def parse_ingredients(value):
    result = {}
    for item in value.split(","):
        name, amount = item.split(":")
        result[name] = int(amount)
    return result


async def recipes_page(update, context):
    conn = db(); rows = conn.execute("SELECT * FROM recipes ORDER BY id").fetchall(); conn.close()
    text = "🍳 منوی غذاها\n\n"
    RECIPE_ALIASES.clear()
    for r in rows:
        RECIPE_ALIASES[r["name"]] = r["id"]
        mins = r["time_seconds"] // 60
        needs = "، ".join(
            f"{INGREDIENT_DISPLAY.get(n, n)}×{v}"
            for n,v in parse_ingredients(r["ingredients"]).items()
        )
        text += f"{r['id']}️⃣ {r['emoji']} {r['name']}\n⏱ {mins} دقیقه | 💵 $ فروش: {r['sell_price']:,}\n🧂 مواد: {needs}\n⌨️ پخت: پخت {r['name']} 1\n\n"
    text += "⚠️ حداکثر 5 سفارش هم‌زمان"
    await update.callback_query.edit_message_text(text, reply_markup=kitchen_back())


async def start_cooking(update, context):
    m = update.message
    parts = m.text.split()
    if len(parts) < 3 or not parts[-1].isdigit():
        await m.reply_text("❌ دستور صحیح: پخت نیمرو 2")
        return
    recipe_name = " ".join(parts[1:-1]).strip()
    quantity = int(parts[-1])
    if quantity <= 0 or quantity > 100:
        await m.reply_text("❌ تعداد باید بین 1 تا 100 باشد.")
        return

    user = m.from_user
    get_player(user)
    ks = kitchen_stats(user.id)
    conn = db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        recipe = conn.execute("SELECT * FROM recipes WHERE name=?", (recipe_name,)).fetchone()
        if not recipe:
            conn.rollback()
            await m.reply_text("❌ این غذا وجود ندارد. اسم غذا را دقیقاً مثل منوی غذاها بنویس.")
            return
        active = conn.execute("SELECT COUNT(*) AS n FROM cooking WHERE user_id=? AND claimed=0", (user.id,)).fetchone()["n"]
        cap = cooking_capacity(ks["level"])
        if active >= cap:
            conn.rollback()
            await m.reply_text(f"🚫 ظرفیت آشپزخانه پر است.\n🔥 {cap}/{cap} سفارش در حال پخت داری.")
            return
        needed = parse_ingredients(recipe["ingredients"])
        missing=[]
        for name,need_per_item in needed.items():
            need = need_per_item * quantity
            row=conn.execute("SELECT amount FROM inventory WHERE user_id=? AND ingredient=?",(user.id,name)).fetchone()
            have=row["amount"] if row else 0
            if have < need:
                missing.append(f"{INGREDIENT_DISPLAY.get(name,name)}: نیاز {need} | موجود {have}")
        if missing:
            conn.rollback()
            await m.reply_text("❌ مواد اولیه کافی نیست:\n"+"\n".join("• "+x for x in missing))
            return
        for name,need_per_item in needed.items():
            conn.execute("UPDATE inventory SET amount=amount-? WHERE user_id=? AND ingredient=?",(need_per_item*quantity,user.id,name))
        now=int(time.time())
        conn.execute("INSERT INTO cooking(user_id,recipe_id,started_at,ready_at,quantity) VALUES(?,?,?,?,?)",(user.id,recipe["id"],now,now+int(recipe["time_seconds"]*chef_speed(ks["chef_level"])),quantity))
        conn.execute("INSERT OR IGNORE INTO daily_activity(user_id,day) VALUES(?,?)",(user.id,time.strftime("%Y-%m-%d")))
        conn.execute("UPDATE daily_activity SET cooked=cooked+? WHERE user_id=? AND day=?",(quantity,user.id,time.strftime("%Y-%m-%d")))
        conn.commit()
        slot=active+1
    finally:
        conn.close()
    await m.reply_text(f"🔥 سفارش ثبت شد\n{recipe['emoji']} {recipe['name']} ×{quantity}\n📍 جایگاه پخت: {slot}/5\n⏱ زمان آماده‌سازی: {recipe['time_seconds']//60} دقیقه\n💵 ارزش فروش هر عدد: {recipe['sell_price']:,} $")


async def cooking_page(update, context):
    user=update.effective_user; get_player(user); now=int(time.time()); conn=db()
    rows=conn.execute("SELECT c.id,c.started_at,c.ready_at,c.quantity,r.name,r.emoji,r.sell_price FROM cooking c JOIN recipes r ON r.id=c.recipe_id WHERE c.user_id=? AND c.claimed=0 ORDER BY c.ready_at",(user.id,)).fetchall(); conn.close()
    ready=sum(1 for r in rows if now>=r["ready_at"]); active=len(rows)
    text=f"🔥 مدیریت پخت\n\n📊 ظرفیت: {active}/5\n🍳 در حال پخت: {active-ready}\n✅ آماده فروش: {ready}\n\n"
    if not rows: text += "آشپزخانه خالی است.\n⌨️ پخت نیمرو 2"
    else:
        for i,r in enumerate(rows,1):
            if now>=r["ready_at"]: text += f"{i}. ✅ {r['emoji']} {r['name']} — آماده فروش 💰 {r['sell_price']:,}\n"
            else: text += f"{i}. ⏳ {r['emoji']} {r['name']} — {r['ready_at']-now} ثانیه باقی‌مانده\n"
    await update.callback_query.edit_message_text(text, reply_markup=kitchen_back())


async def food_sell_page(update, context):
    user=update.effective_user; now=int(time.time()); conn=db()
    rows=conn.execute("SELECT c.id,c.quantity,c.ready_at,r.name,r.emoji,r.sell_price FROM cooking c JOIN recipes r ON r.id=c.recipe_id WHERE c.user_id=? AND c.claimed=0 ORDER BY c.ready_at",(user.id,)).fetchall(); conn.close()
    ready=[r for r in rows if now>=r["ready_at"]]
    if not ready: await update.callback_query.edit_message_text("📦 غذای آماده‌ای برای فروش نداری.\n🔥 وقتی زمان پخت تمام شد اینجا ظاهر می‌شود.",reply_markup=kitchen_back()); return
    buttons=[]; text="📦 فروشگاه غذای آماده\n\n"
    for r in ready:
        total=r["sell_price"]*r["quantity"]; text+=f"{r['emoji']} {r['name']} ×{r['quantity']} | 💰 {total:,} $\n"; buttons.append([InlineKeyboardButton(f"💰 فروش {r['emoji']} {r['name']}",callback_data=f"sell_food_{r['id']}")])
    buttons.append([InlineKeyboardButton("🔙 آشپزخانه",callback_data="kitchen")])
    await update.callback_query.edit_message_text(text,reply_markup=InlineKeyboardMarkup(buttons))


async def sell_food(update, context, cooking_id):
    user=update.effective_user; now=int(time.time()); conn=db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row=conn.execute("SELECT c.id,c.quantity,c.ready_at,r.sell_price,r.name,r.emoji FROM cooking c JOIN recipes r ON r.id=c.recipe_id WHERE c.id=? AND c.user_id=? AND c.claimed=0",(cooking_id,user.id)).fetchone()
        if not row: conn.rollback(); await update.callback_query.answer("این سفارش قبلاً فروخته شده یا وجود ندارد.",show_alert=True); return
        if now<row["ready_at"]: conn.rollback(); await update.callback_query.answer("هنوز آماده نشده.",show_alert=True); return
        total=row["sell_price"]*row["quantity"]; conn.execute("UPDATE cooking SET claimed=1 WHERE id=?",(cooking_id,)); conn.execute("UPDATE players SET coins=coins+? WHERE user_id=?",(total,user.id)); conn.commit()
    finally: conn.close()
    await update.callback_query.edit_message_text(f"✅ فروش موفق بود!\n{row['emoji']} {row['name']} ×{row['quantity']}\n💰 +{total:,} $",reply_markup=kitchen_back())


# -------------------- CUSTOMER / UPGRADES / MISSIONS --------------------

async def orders_page(update, context):
    user=update.effective_user; get_player(user); now=int(time.time()); conn=db()
    conn.execute("UPDATE customer_orders SET claimed=1 WHERE user_id=? AND claimed=0 AND expires_at<?",(user.id,now))
    rows=conn.execute("SELECT o.id,o.quantity,o.reward,r.name,r.emoji,o.expires_at FROM customer_orders o JOIN recipes r ON r.id=o.recipe_id WHERE o.user_id=? AND o.claimed=0 ORDER BY o.id",(user.id,)).fetchall()
    if not rows:
        recipes=conn.execute("SELECT * FROM recipes ORDER BY id").fetchall(); chosen=random.sample(recipes,min(3,len(recipes)))
        for r in chosen:
            qty=random.randint(1,3); reward=int(r['sell_price']*qty*1.15); conn.execute("INSERT INTO customer_orders(user_id,recipe_id,quantity,reward,created_at,expires_at) VALUES(?,?,?,?,?,?)",(user.id,r['id'],qty,reward,now,now+3600))
        conn.commit(); rows=conn.execute("SELECT o.id,o.quantity,o.reward,r.name,r.emoji,o.expires_at FROM customer_orders o JOIN recipes r ON r.id=o.recipe_id WHERE o.user_id=? AND o.claimed=0 ORDER BY o.id",(user.id,)).fetchall()
    conn.close(); buttons=[]; text="📋 سفارش‌های مشتری\n\n"
    for r in rows:
        text+=f"{r['emoji']} {r['name']} ×{r['quantity']}  → 💵 {r['reward']:,} $\n"; buttons.append([InlineKeyboardButton(f"تحویل {r['emoji']} {r['name']}",callback_data=f"order_{r['id']}")])
    buttons.append([InlineKeyboardButton("🔄 سفارش‌های جدید",callback_data="orders_new")]); buttons.append([InlineKeyboardButton("🔙 آشپزخانه",callback_data="kitchen")])
    await update.callback_query.edit_message_text(text,reply_markup=InlineKeyboardMarkup(buttons))


async def claim_order(update, context, order_id):
    user=update.effective_user; now=int(time.time()); conn=db()
    row=conn.execute("SELECT o.*,r.name,r.emoji FROM customer_orders o JOIN recipes r ON r.id=o.recipe_id WHERE o.id=? AND o.user_id=? AND o.claimed=0",(order_id,user.id)).fetchone()
    if not row: conn.close(); await update.callback_query.answer("این سفارش دیگر فعال نیست.",show_alert=True); return
    if now>row['expires_at']: conn.close(); await update.callback_query.answer("زمان سفارش تمام شده.",show_alert=True); return
    stock=conn.execute("SELECT COALESCE(SUM(c.quantity),0) n FROM cooking c WHERE c.user_id=? AND c.recipe_id=? AND c.claimed=0 AND c.ready_at<=?",(user.id,row['recipe_id'],now)).fetchone()['n']
    if stock < row['quantity']: conn.close(); await update.callback_query.answer("غذای کافی آماده نداری.",show_alert=True); return
    need=row['quantity']; ids=conn.execute("SELECT id,quantity FROM cooking WHERE user_id=? AND recipe_id=? AND claimed=0 AND ready_at<=? ORDER BY ready_at",(user.id,row['recipe_id'],now)).fetchall()
    for x in ids:
        take=min(need,x['quantity']); remain=x['quantity']-take; conn.execute("UPDATE cooking SET quantity=?, claimed=? WHERE id=?",(remain,1 if remain==0 else 0,x['id'])); need-=take
        if need==0: break
    conn.execute("UPDATE customer_orders SET claimed=1 WHERE id=?",(order_id,)); conn.execute("UPDATE players SET coins=coins+? WHERE user_id=?",(row['reward'],user.id)); conn.execute("INSERT OR IGNORE INTO daily_activity(user_id,day) VALUES(?,?)",(user.id,time.strftime('%Y-%m-%d'))); conn.execute("UPDATE daily_activity SET sold=sold+?, revenue=revenue+? WHERE user_id=? AND day=?",(row['quantity'],row['reward'],user.id,time.strftime('%Y-%m-%d'))); conn.commit(); conn.close()
    await update.callback_query.edit_message_text(f"✅ سفارش تحویل شد!\n{row['emoji']} {row['name']} ×{row['quantity']}\n💵 +{row['reward']:,} $",reply_markup=kitchen_back())


async def kitchen_upgrade_page(update, context):
    user=update.effective_user; ks=kitchen_stats(user.id); costs=(5000*ks['level']); cap=cooking_capacity(ks['level']); conn=db(); coins=conn.execute("SELECT coins FROM players WHERE user_id=?",(user.id,)).fetchone()['coins']; conn.close()
    text=f"🏪 ارتقای آشپزخانه\n\nسطح فعلی: {ks['level']}\nظرفیت پخت: {cap}\n\nارتقای بعدی: {costs:,} $\n💵 موجودی: {coins:,} $"
    await update.callback_query.edit_message_text(text,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"⬆️ ارتقا ({costs:,} $)",callback_data="upgrade_kitchen")],[InlineKeyboardButton("📦 ارتقای انبار",callback_data="upgrade_storage")],[InlineKeyboardButton("🔙 آشپزخانه",callback_data="kitchen")]]))


async def upgrade_kitchen(update, context):
    user=update.effective_user; ks=kitchen_stats(user.id); cost=5000*ks['level']; conn=db(); p=conn.execute("SELECT coins FROM players WHERE user_id=?",(user.id,)).fetchone()
    if p['coins']<cost: conn.close(); await update.callback_query.answer("$ کافی نیست.",show_alert=True); return
    conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?",(cost,user.id)); conn.execute("UPDATE kitchen_stats SET level=level+1 WHERE user_id=?",(user.id,)); conn.commit(); conn.close(); await update.callback_query.answer("آشپزخانه ارتقا یافت!",show_alert=True); await kitchen_upgrade_page(update,context)


async def upgrade_storage(update, context):
    user=update.effective_user; ks=kitchen_stats(user.id); cost=3000*ks['storage_level']; conn=db(); p=conn.execute("SELECT coins FROM players WHERE user_id=?",(user.id,)).fetchone()
    if p['coins']<cost: conn.close(); await update.callback_query.answer("$ کافی نیست.",show_alert=True); return
    conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?",(cost,user.id)); conn.execute("UPDATE kitchen_stats SET storage_level=storage_level+1 WHERE user_id=?",(user.id,)); conn.commit(); conn.close(); await update.callback_query.answer("ظرفیت انبار افزایش یافت!",show_alert=True); await kitchen_upgrade_page(update,context)


async def chefs_page(update, context):
    user=update.effective_user; ks=kitchen_stats(user.id); cost=4000*ks['chef_level']; text=f"🧑‍🍳 آشپزها\n\nسطح آشپز: {ks['chef_level']}\n⚡ سرعت پخت: {int(chef_speed(ks['chef_level'])*100)}%\n\nارتقای بعدی: {cost:,} $"
    await update.callback_query.edit_message_text(text,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"⬆️ ارتقای آشپز ({cost:,} $)",callback_data="upgrade_chef")],[InlineKeyboardButton("🔙 آشپزخانه",callback_data="kitchen")]]))


async def upgrade_chef(update, context):
    user=update.effective_user; ks=kitchen_stats(user.id); cost=4000*ks['chef_level']; conn=db(); p=conn.execute("SELECT coins FROM players WHERE user_id=?",(user.id,)).fetchone()
    if p['coins']<cost: conn.close(); await update.callback_query.answer("$ کافی نیست.",show_alert=True); return
    conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?",(cost,user.id)); conn.execute("UPDATE kitchen_stats SET chef_level=chef_level+1 WHERE user_id=?",(user.id,)); conn.commit(); conn.close(); await update.callback_query.answer("آشپز ارتقا یافت!",show_alert=True); await chefs_page(update,context)


async def daily_mission_page(update, context):
    user=update.effective_user; a=ensure_daily(user.id); target=5; reward=2500; text=f"🎯 ماموریت روزانه\n\n🍳 پخت امروز: {a['cooked']}/{target}\n\n🎁 جایزه: {reward:,} $"
    buttons=[]
    if a['cooked']>=target and not a['mission_claimed']: buttons.append([InlineKeyboardButton("🎁 دریافت جایزه",callback_data="claim_mission")])
    elif a['mission_claimed']: text+="\n\n✅ جایزه امروز را گرفتی."
    buttons.append([InlineKeyboardButton("🔙 آشپزخانه",callback_data="kitchen")]); await update.callback_query.edit_message_text(text,reply_markup=InlineKeyboardMarkup(buttons))


async def claim_mission(update, context):
    user=update.effective_user; a=ensure_daily(user.id)
    if a['cooked']<5 or a['mission_claimed']: await update.callback_query.answer("ماموریت هنوز کامل نشده.",show_alert=True); return
    conn=db(); conn.execute("UPDATE daily_activity SET mission_claimed=1 WHERE user_id=? AND day=?",(user.id,time.strftime('%Y-%m-%d'))); conn.execute("UPDATE players SET coins=coins+2500 WHERE user_id=?",(user.id,)); conn.commit(); conn.close(); await update.callback_query.answer("جایزه دریافت شد!",show_alert=True); await daily_mission_page(update,context)


# -------------------- FANTASY LAB + INCIDENT --------------------

def lab_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 محصولات", callback_data="products")],
        [InlineKeyboardButton("⏳ تولیدهای من", callback_data="production")],
        [InlineKeyboardButton("💰 فروش محصول", callback_data="product_sell")],
        [InlineKeyboardButton("⚔️ درگیری خیالی", callback_data="incident_info")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="kingdom")],
    ])


async def lab_page(update, context):
    await update.callback_query.edit_message_text(
        "🧪 کارخانه فانتزی\n\n"
        "محصولات این بخش کاملاً خیالی هستند.\n"
        "تولیدها زمان‌بر و پرریسک‌اند و فروش آن‌ها سود بالاتری دارد.",
        reply_markup=lab_menu(),
    )


async def products_page(update, context):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM fantasy_products ORDER BY cost"
    ).fetchall()
    conn.close()

    text = "🧪 محصولات فانتزی\n\n"
    for r in rows:
        hours = r["time_seconds"] // 3600
        text += (
            f"{r['emoji']} {r['name']}\n"
            f"💸 هزینه: {r['cost']:,}\n"
            f"⏱ زمان: {hours} ساعت\n"
            f"💰 فروش: {r['sell_price']:,}\n"
            f"⚠️ ریسک: {r['risk']}%\n\n"
        )

    text += "برای شروع تولید: تولید 1"

    await update.callback_query.edit_message_text(
        text,
        reply_markup=back_lab(),
    )


def back_lab():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data="lab")]
    ])


async def start_production(update, context):
    m = update.message
    parts = m.text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        await m.reply_text("❌ مثال: تولید 1")
        return

    product_id = int(parts[1])
    user = m.from_user
    get_player(user)

    conn = db()
    product = conn.execute(
        "SELECT * FROM fantasy_products WHERE id=?",
        (product_id,),
    ).fetchone()

    if not product:
        conn.close()
        await m.reply_text("❌ محصول وجود ندارد.")
        return

    try:
        conn.execute("BEGIN IMMEDIATE")

        p = conn.execute(
            "SELECT coins FROM players WHERE user_id=?",
            (user.id,),
        ).fetchone()

        if p["coins"] < product["cost"]:
            conn.rollback()
            await m.reply_text("❌ $ کافی نیست.")
            return

        conn.execute(
            "UPDATE players SET coins=coins-? WHERE user_id=?",
            (product["cost"], user.id),
        )

        now = int(time.time())
        conn.execute("""
            INSERT INTO production
            (user_id,product_id,started_at,ready_at,quantity)
            VALUES(?,?,?,?,1)
        """, (
            user.id,
            product_id,
            now,
            now + product["time_seconds"],
        ))

        conn.commit()
    finally:
        conn.close()

    await m.reply_text(
        f"⏳ تولید {product['emoji']} {product['name']} شروع شد.\n"
        f"زمان: {product['time_seconds']//3600} ساعت"
    )


async def production_page(update, context):
    user = update.effective_user()
    now = int(time.time())

    conn = db()
    rows = conn.execute("""
        SELECT p.id,p.ready_at,p.quantity,f.name,f.emoji
        FROM production p
        JOIN fantasy_products f ON f.id=p.product_id
        WHERE p.user_id=? AND p.claimed=0
        ORDER BY p.ready_at
    """, (user.id,)).fetchall()
    conn.close()

    if not rows:
        text = "⏳ تولید فعالی نداری."
    else:
        text = "⏳ تولیدهای من\n\n"
        for r in rows:
            if now >= r["ready_at"]:
                text += f"✅ {r['emoji']} {r['name']} آماده است.\n"
            else:
                text += f"⏳ {r['emoji']} {r['name']} — {r['ready_at']-now} ثانیه\n"

    await update.callback_query.edit_message_text(
        text,
        reply_markup=back_lab(),
    )


async def product_sell_page(update, context):
    user = update.effective_user
    now = int(time.time())

    conn = db()
    rows = conn.execute("""
        SELECT p.id,p.ready_at,p.quantity,f.name,f.emoji,f.sell_price
        FROM production p
        JOIN fantasy_products f ON f.id=p.product_id
        WHERE p.user_id=? AND p.claimed=0
    """, (user.id,)).fetchall()
    conn.close()

    ready = [r for r in rows if now >= r["ready_at"]]

    if not ready:
        text = "📦 محصول آماده‌ای برای فروش نداری."
        keyboard = back_lab()
    else:
        text = "📦 محصولات آماده\n\n"
        buttons = []

        for r in ready:
            text += (
                f"{r['emoji']} {r['name']} ×{r['quantity']}\n"
                f"💰 فروش: {r['sell_price']*r['quantity']:,}\n\n"
            )
            buttons.append([
                InlineKeyboardButton(
                    f"💰 فروش {r['emoji']} {r['name']}",
                    callback_data=f"sell_product_{r['id']}",
                )
            ])

        buttons.append([
            InlineKeyboardButton("🔙 برگشت", callback_data="lab")
        ])
        keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.edit_message_text(
        text,
        reply_markup=keyboard,
    )


async def sell_product(update, context, production_id):
    user = update.effective_user
    now = int(time.time())

    conn = db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute("""
            SELECT p.id,p.quantity,p.ready_at,f.name,f.emoji,f.sell_price,f.risk
            FROM production p
            JOIN fantasy_products f ON f.id=p.product_id
            WHERE p.id=? AND p.user_id=? AND p.claimed=0
        """, (production_id, user.id)).fetchone()

        if not row:
            conn.rollback()
            await update.callback_query.answer("محصول پیدا نشد.", show_alert=True)
            return

        if now < row["ready_at"]:
            conn.rollback()
            await update.callback_query.answer(
                "هنوز آماده نشده.",
                show_alert=True,
            )
            return

        total = row["sell_price"] * row["quantity"]

        # درگیری کاملاً فانتزی: ممکن است فروش با یک NPC خیالی به حادثه ختم شود.
        incident = random.randint(1, 100) <= row["risk"]

        if incident:
            loss = min(total, max(1000, total // 4))
            reward = total - loss

            conn.execute(
                "UPDATE players SET coins=coins+? WHERE user_id=?",
                (reward, user.id),
            )
            conn.execute(
                "UPDATE players SET health=MAX(1,health-10) WHERE user_id=?",
                (user.id,),
            )
            conn.execute(
                "UPDATE production SET claimed=1 WHERE id=?",
                (production_id,),
            )
            conn.execute("""
                INSERT INTO incidents(user_id,product_id,created_at)
                VALUES(?,?,?)
            """, (user.id, 1, now))

            conn.commit()

            text = (
                "⚠️ درگیری خیالی!\n\n"
                "یک NPC فانتزی هنگام معامله دردسر درست کرد.\n"
                f"💰 دریافتی بعد از خسارت: {reward:,} $\n"
                f"❤️ سلامتی: 10 واحد کم شد."
            )
        else:
            conn.execute(
                "UPDATE players SET coins=coins+? WHERE user_id=?",
                (total, user.id),
            )
            conn.execute(
                "UPDATE production SET claimed=1 WHERE id=?",
                (production_id,),
            )
            conn.commit()

            text = (
                f"✅ فروش موفق!\n"
                f"{row['emoji']} {row['name']} ×{row['quantity']}\n"
                f"💰 +{total:,} $"
            )

    finally:
        conn.close()

    await update.callback_query.edit_message_text(
        text,
        reply_markup=back_lab(),
    )


async def incident_info(update, context):
    await update.callback_query.edit_message_text(
        "⚔️ درگیری خیالی\n\n"
        "بعضی محصولات ریسک بالایی دارند. هنگام فروش ممکن است "
        "یک NPC فانتزی دردسر ایجاد کند.\n\n"
        "در صورت حادثه، بخشی از درآمد از بین می‌رود و "
        "ممکن است سلامتی داخل بازی کاهش پیدا کند.",
        reply_markup=back_lab(),
    )


# -------------------- GAMBLING --------------------

GAMBLING_MIN_BET = 1
GAMBLING_MAX_BET = 10**12


def gamble_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎲 تاس", callback_data="dice"),
            InlineKeyboardButton("🎰 اسلات", callback_data="slots"),
        ],
        [InlineKeyboardButton("🔙 برگشت", callback_data="kingdom")],
    ])


def gambling_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 قمار", callback_data="gamble")],
        [InlineKeyboardButton("🔙 قلمرو", callback_data="kingdom")],
    ])


async def gamble_page(update, context):
    p = get_player(update.effective_user)
    await update.callback_query.edit_message_text(
        f"🎰 قمار\n\n💰 موجودی: {p['coins']:,} $\n\n"
        "🎲 تاس:\n"
        "تاس زوج 500\n"
        "تاس فرد 2500\n\n"
        "🎰 اسلات:\n"
        "اسلات 500\n"
        "اسلات 2500\n\n"
        "مبلغ دلخواه خودت را جایگزین کن؛ فقط باید موجودی کافی داشته باشی.",
        reply_markup=gamble_menu(),
    )


async def dice_page(update, context):
    p = get_player(update.effective_user)
    await update.callback_query.edit_message_text(
        f"🎲 تاس\n\n💰 موجودی: {p['coins']:,}\n\n"
        "در پیام بنویس:\n"
        "🎲 تاس زوج 500\n"
        "🎲 تاس فرد 2500\n\n"
        "مبلغ شرط آزاد است و تا سقف موجودی تو می‌تواند باشد.",
        reply_markup=gambling_back(),
    )


async def slots_page(update, context):
    p = get_player(update.effective_user)
    await update.callback_query.edit_message_text(
        f"🎰 اسلات\n\n💰 موجودی: {p['coins']:,}\n\n"
        "در پیام بنویس:\n"
        "🎰 اسلات 500\n"
        "🎰 اسلات 2500\n\n"
        "مبلغ شرط آزاد است و تا سقف موجودی تو می‌تواند باشد.\n"
        "ربات خودش انیمیشن واقعی اسلات تلگرام را می‌فرستد.",
        reply_markup=gambling_back(),
    )


def deduct(user_id, amount):
    conn = db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT coins FROM players WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if not row or row["coins"] < amount:
            conn.rollback()
            return False
        conn.execute(
            "UPDATE players SET coins=coins-? WHERE user_id=?",
            (amount, user_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def add_coins(user_id, amount):
    conn = db()
    conn.execute(
        "UPDATE players SET coins=coins+? WHERE user_id=?",
        (amount, user_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT coins FROM players WHERE user_id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row["coins"]


def current_balance(user_id):
    conn = db()
    row = conn.execute(
        "SELECT coins FROM players WHERE user_id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row["coins"] if row else 0


def parse_bet_command(text, game):
    parts = text.strip().split()
    if game == "dice":
        if len(parts) != 3 or parts[0] != "تاس" or parts[1] not in ("زوج", "فرد"):
            return None, None, "❌ دستور صحیح:\nتاس زوج 500\nیا\nتاس فرد 500"
        try:
            amount = int(parts[2].replace(",", ""))
        except ValueError:
            return None, None, "❌ مبلغ باید عدد صحیح باشد. مثال: تاس زوج 500"
        return parts[1], amount, None

    if len(parts) != 2 or parts[0] != "اسلات":
        return None, None, "❌ دستور صحیح:\nاسلات 500"
    try:
        amount = int(parts[1].replace(",", ""))
    except ValueError:
        return None, None, "❌ مبلغ باید عدد صحیح باشد. مثال: اسلات 500"
    return None, amount, None


def validate_bet(user_id, amount):
    if amount < GAMBLING_MIN_BET:
        return False, "❌ مبلغ شرط باید حداقل 1 $ باشد."
    if amount > GAMBLING_MAX_BET:
        return False, "❌ مبلغ شرط بیش از حد مجاز است."
    balance = current_balance(user_id)
    if amount > balance:
        return False, f"❌ $ کافی نیست.\n💰 موجودی: {balance:,}\n💸 شرط: {amount:,}"
    return True, None


async def text_dice(update, context, choice, amount):
    user = update.effective_user
    ok, error = validate_bet(user.id, amount)
    if not ok:
        await update.message.reply_text(error)
        return
    if not deduct(user.id, amount):
        await update.message.reply_text("❌ موجودی تغییر کرده است؛ دوباره تلاش کن.")
        return

    # Telegram خودش انیمیشن واقعی تاس را ارسال می‌کند.
    dice_message = await context.bot.send_dice(
        chat_id=update.effective_chat.id,
        emoji="🎲",
    )
    number = dice_message.dice.value
    won = (choice == "زوج" and number % 2 == 0) or (choice == "فرد" and number % 2 == 1)

    if won:
        payout = amount * 2
        balance = add_coins(user.id, payout)
        result = (
            f"🎉 **بردی!**\n"
            f"🎲 عدد تاس: {number}\n"
            f"🟢 حدس تو: {choice}\n"
            f"💰 سود خالص: +{amount:,} $\n"
            f"💳 موجودی: {balance:,}"
        )
    else:
        balance = current_balance(user.id)
        result = (
            f"💀 **باختی!**\n"
            f"🎲 عدد تاس: {number}\n"
            f"🔴 حدس تو: {choice}\n"
            f"💸 مبلغ از دست‌رفته: {amount:,} $\n"
            f"💳 موجودی: {balance:,}"
        )
    await dice_message.reply_text(result, parse_mode="Markdown")


async def text_slots(update, context, amount):
    user = update.effective_user
    ok, error = validate_bet(user.id, amount)
    if not ok:
        await update.message.reply_text(error)
        return
    if not deduct(user.id, amount):
        await update.message.reply_text("❌ موجودی تغییر کرده است؛ دوباره تلاش کن.")
        return

    # Telegram خودش انیمیشن واقعی اسلات را ارسال می‌کند.
    slot_message = await context.bot.send_dice(
        chat_id=update.effective_chat.id,
        emoji="🎰",
    )
    value = slot_message.dice.value

    # مقدار رسمی اسلات تلگرام 1..64 است. برای بازی، چند سطح برد تعریف شده.
    if value == 64:
        multiplier = 20
        title = "💎 جک‌پات!"
    elif value >= 60:
        multiplier = 10
        title = "🔥 برد بزرگ!"
    elif value >= 45:
        multiplier = 5
        title = "🎉 برد!"
    elif value >= 30:
        multiplier = 2
        title = "✨ برد!"
    else:
        multiplier = 0
        title = "💀 باختی!"

    if multiplier:
        payout = amount * multiplier
        balance = add_coins(user.id, payout)
        result = (
            f"{title}\n"
            f"🎰 نتیجه اسلات: {value}\n"
            f"🎯 ضریب: ×{multiplier}\n"
            f"💰 پرداختی: {payout:,} $\n"
            f"💳 موجودی: {balance:,}"
        )
    else:
        balance = current_balance(user.id)
        result = (
            f"{title}\n"
            f"🎰 نتیجه اسلات: {value}\n"
            f"💸 مبلغ از دست‌رفته: {amount:,} $\n"
            f"💳 موجودی: {balance:,}"
        )
    await slot_message.reply_text(result)


# Backward-compatible callback handlers for the glass buttons.
async def dice_bet(update, amount):
    await update.callback_query.answer(
        "برای بازی در پیام بنویس: تاس زوج 500 یا تاس فرد 500",
        show_alert=True,
    )


async def play_slots(update, amount):
    await update.callback_query.answer(
        "برای بازی در پیام بنویس: اسلات 500",
        show_alert=True,
    )


# -------------------- OTHER PAGES --------------------

async def simple_page(update, title, text):
    await update.callback_query.edit_message_text(
        f"{title}\n\n{text}",
        reply_markup=back(),
    )


# -------------------- CALLBACK HANDLER --------------------

async def callbacks(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "kingdom":
        await show_kingdom(update, context)

    elif data == "profile":
        await profile(update, context)

    elif data == "crypto":
        await crypto_page(update, context)

    elif data == "crypto_list":
        await crypto_list(update, context)

    elif data == "crypto_wallet":
        await crypto_wallet(update, context)

    elif data == "kitchen":
        await kitchen(update, context)

    elif data == "ingredients":
        await ingredients_page(update, context)

    elif data == "recipes":
        await recipes_page(update, context)

    elif data == "cooking":
        await cooking_page(update, context)

    elif data == "kitchen_inventory":
        await kitchen_inventory_page(update, context)

    elif data == "food_sell":
        await food_sell_page(update, context)

    elif data == "orders":
        await orders_page(update, context)

    elif data == "orders_new":
        conn=db(); conn.execute("UPDATE customer_orders SET claimed=1 WHERE user_id=? AND claimed=0",(update.effective_user.id,)); conn.commit(); conn.close(); await orders_page(update, context)

    elif data.startswith("order_"):
        await claim_order(update, context, int(data.split("_")[-1]))

    elif data == "kitchen_upgrade":
        await kitchen_upgrade_page(update, context)

    elif data == "upgrade_kitchen":
        await upgrade_kitchen(update, context)

    elif data == "upgrade_storage":
        await upgrade_storage(update, context)

    elif data == "chefs":
        await chefs_page(update, context)

    elif data == "upgrade_chef":
        await upgrade_chef(update, context)

    elif data == "daily_mission":
        await daily_mission_page(update, context)

    elif data == "claim_mission":
        await claim_mission(update, context)

    elif data.startswith("sell_food_"):
        await sell_food(update, context, int(data.split("_")[-1]))

    elif data == "lab":
        await lab_page(update, context)

    elif data == "products":
        await products_page(update, context)

    elif data == "production":
        await production_page(update, context)

    elif data == "product_sell":
        await product_sell_page(update, context)

    elif data.startswith("sell_product_"):
        await sell_product(update, context, int(data.split("_")[-1]))

    elif data == "incident_info":
        await incident_info(update, context)

    elif data == "gamble":
        await gamble_page(update, context)

    elif data == "dice":
        await dice_page(update, context)

    elif data == "slots":
        await slots_page(update, context)

    elif data.startswith("bet_dice_"):
        await dice_bet(update, int(data.split("_")[-1]))

    elif data.startswith("bet_slots_"):
        await play_slots(update, int(data.split("_")[-1]))

    elif data.startswith("dice_even_"):
        await roll_dice(update, int(data.split("_")[-1]), "even")

    elif data.startswith("dice_odd_"):
        await roll_dice(update, int(data.split("_")[-1]), "odd")

    elif data == "attack":
        await simple_page(
            update,
            "⚔️ حمله",
            "سیستم حمله در نسخه بعدی قابل گسترش است.",
        )

    elif data == "smuggle":
        await simple_page(
            update,
            "🕵️ قاچاق",
            "این بخش در این نسخه فقط نمایشی است.",
        )

    elif data == "captives":
        await simple_page(
            update,
            "⛓️ اسیران",
            "سیستم اسیران در نسخه بعدی قابل گسترش است.",
        )

    elif data == "black_market":
        await simple_page(
            update,
            "🏴‍☠️ بازار سیاه",
            "بازار فانتزی بازی در نسخه بعدی قابل گسترش است.",
        )

    elif data == "safe":
        await simple_page(
            update,
            "🏦 بانک",
            "بانک برای نگهداری $‌ها در نسخه بعدی قابل گسترش است.",
        )

    elif data == "building":
        await simple_page(
            update,
            "🏗 ساخت‌وساز",
            "سیستم ساخت‌وساز در نسخه بعدی قابل گسترش است.",
        )


# -------------------- TEXT HANDLER --------------------

async def text_handler(update, context):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if text.lower() in {"مانی", "many", "منو"}:
        await show_kingdom(update, context)

    elif text in {"آشپزخانه برو", "آشپز خانه برو"}:
        await kitchen(update, context)

    elif text in {"خرید مواد غذایی", "خرید مواد اولیه"}:
        await update.message.reply_text("🛒 برای خرید، نام ماده غذایی و تعداد را بنویس.\nمثال: خرید تخمه مرغ 5")

    elif text in {"سفارش مشتری", "سفارش ها", "سفارش‌ها"}:
        await update.message.reply_text("📋 سفارش مشتری را از دکمه داخل آشپزخانه باز کن.")

    elif text in {"منوی غذاها", "منو غذاها"}:
        await update.message.reply_text("🍳 منوی غذاها\n\nبرای دیدن کامل مواد و زمان هر غذا، از دکمه «🍳 منوی غذاها» داخل آشپزخانه استفاده کن.")

    elif text == "خایمالی":
        await hunt(update, context)

    elif text == "خفت گیری":
        await rip(update, context)

    elif text.startswith("اهدای باج "):
        await transfer(update, context)

    elif text.startswith("خرید "):
        # Crypto purchases keep their old 3-part syntax; kitchen purchases may have multi-word Persian names.
        parts = text.split()
        if len(parts) == 3 and parts[1].upper() in {"BTC","ETH","USDT","BNB","XRP","SOL","USDC","DOGE","TRX","ADA"}:
            await crypto_trade(update, True)
        else:
            await buy_ingredient(update, context)

    elif text.startswith("فروش ") and len(text.split()) == 3:
        await crypto_trade(update, False)

    elif text.startswith("پخت "):
        await start_cooking(update, context)

    elif text == "موجودی آشپزخانه":
        await kitchen_inventory_page(update, context)

    elif text.startswith("تاس "):
        choice, amount, error = parse_bet_command(text, "dice")
        if error:
            await update.message.reply_text(error)
        else:
            await text_dice(update, context, choice, amount)

    elif text.startswith("اسلات "):
        _, amount, error = parse_bet_command(text, "slots")
        if error:
            await update.message.reply_text(error)
        else:
            await text_slots(update, context, amount)



# -------------------- START --------------------

async def start(update, context):
    await update.message.reply_text(
        "👑 به بازی مانی خوش آمدی!\n\n"
        "برای ورود به منوی بازی یکی از این کلمات را داخل گروه بنویس:\n"
        "مانی | many | منو"
    )


def main():
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است. "
            "توکن ربات را در متغیر محیطی BOT_TOKEN قرار بده."
        )

    init_db()

    app = Application.builder().token(token).build()

    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/start$"), start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Kingdom bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
