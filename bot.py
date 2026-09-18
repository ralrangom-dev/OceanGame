import os
import sqlite3
import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# Telegram inline-button styles: primary=blue, success=green, danger=red.
def B(text, callback_data, style="primary"):
    return InlineKeyboardButton(text=text, callback_data=callback_data, style=style)


TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "oceangame.db"

# -------------------- Database --------------------

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
            bank_profit INTEGER NOT NULL DEFAULT 0,
            bank_last_day INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, item_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS crypto (
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, symbol)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            user_id INTEGER NOT NULL,
            car_id TEXT NOT NULL,
            car_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            PRIMARY KEY (user_id, car_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS income_businesses (
            user_id INTEGER NOT NULL,
            business_id TEXT NOT NULL,
            business_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            income INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            last_income INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, business_id)
        )
    """)

    # Upgrade older OceanGame databases without deleting player data.
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(players)").fetchall()}
    if "bank_profit" not in columns:
        conn.execute("ALTER TABLE players ADD COLUMN bank_profit INTEGER NOT NULL DEFAULT 0")
    if "bank_last_day" not in columns:
        conn.execute("ALTER TABLE players ADD COLUMN bank_last_day INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()


def get_player(user):
    conn = db()
    row = conn.execute(
        "SELECT * FROM players WHERE user_id=?",
        (user.id,)
    ).fetchone()

    if row is None:
        conn.execute(
            """
            INSERT INTO players(
                user_id, name, coins, bank, level,
                bank_profit, bank_last_day, created_at
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                user.id,
                user.first_name or "بازیکن",
                0,
                0,
                1,
                0,
                int(time.time() // 86400),
                int(time.time()),
            ),
        )
        conn.commit()
    else:
        conn.execute(
            "UPDATE players SET name=? WHERE user_id=?",
            (user.first_name or row["name"], user.id)
        )
        conn.commit()

    row = conn.execute(
        "SELECT * FROM players WHERE user_id=?",
        (user.id,)
    ).fetchone()
    conn.close()

    apply_bank_interest(user.id)
    return get_player_raw(user.id)


def get_player_raw(user_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM players WHERE user_id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    return row


def apply_bank_interest(user_id):
    """
    Bank UI shows 1% daily profit.
    Interest is accumulated once per day and is not mixed into bank principal.
    """
    conn = db()
    row = conn.execute(
        "SELECT bank, bank_profit, bank_last_day FROM players WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if row is None:
        conn.close()
        return

    today = int(time.time() // 86400)
    last_day = int(row["bank_last_day"] or today)

    if today > last_day and row["bank"] > 0:
        days = min(today - last_day, 30)
        profit = int(row["bank"] * 0.01 * days)
        conn.execute(
            """
            UPDATE players
            SET bank_profit=bank_profit+?, bank_last_day=?
            WHERE user_id=?
            """,
            (profit, today, user_id),
        )
    elif today > last_day:
        conn.execute(
            "UPDATE players SET bank_last_day=? WHERE user_id=?",
            (today, user_id),
        )

    conn.commit()
    conn.close()


# -------------------- Game data --------------------

CARS = [
    ("pride", "پراید", 80000),
    ("peugeot206", "پژو ۲۰۶", 250000),
    ("samand", "سمند", 400000),
    ("shahin", "شاهین", 800000),
    ("bmw", "BMW", 2500000),
    ("mercedes_benz", "مرسدس بنز", 4000000),
    ("ferrari", "فراری", 10000000),
    ("bugatti", "بوگاتی", 30000000),
]

CRYPTO = {
    "ADA": 1.003,
    "BTC": 10410.243,
    "DOGE": 0.244,
    "ETH": 1296.764,
    "GOLD": 2038.289,
    "OCEAN": 22.835,
    "OIL": 65.093,
    "PEPE": 0.019,
    "SHIB": 0.004,
    "SILVER": 25.014,
    "SOL": 121.334,
    "TON": 4.477,
    "USDT": 0.852,
    "XRP": 2.878,
}

CRYPTO_NAMES = {
    "ADA": "کاردانو",
    "BTC": "بیتکوین",
    "DOGE": "دوج کوین",
    "ETH": "اتریوم",
    "GOLD": "طلا",
    "OCEAN": "اوشن",
    "OIL": "نفت",
    "PEPE": "پپه",
    "SHIB": "شیبا",
    "SILVER": "نقره",
    "SOL": "سولانا",
    "TON": "تون کوین",
    "USDT": "تتر",
    "XRP": "ریپل",
}

BLACK_MARKET = [
    ("SW001", "چاقو", 2000, "🔪"),
    ("HT01", "نقاب خیابانی", 2000, "🎭"),
    ("HT02", "موتور فرار", 2000, "🏍️"),
    ("SW002", "شمشیر چوبی", 2000, "🗡️"),
    ("MUG01", "دستکش بی‌ردپا", 2000, "🧤"),
    ("HT01B", "ماسک سرقت", 3000, "🎭"),
    ("POTION", "معجون سلامتی", 3200, "🧪"),
    ("AR001", "زره چرمی", 3200, "🛡️"),
]

# Items visible in the inventory screenshot. These can be expanded by the store later.
INVENTORY_EXTRA = [
    ("DOG", "سگ", "🐶"),
    ("CAMERA", "مسدودکننده دوربین", "📷"),
    ("MONEY_CARD", "جعل کننده کارت", "💳"),
]

# -------------------- Store items --------------------

SHOP_ITEMS = {
    "shop_baby": [
        ("baby_milk", "شیر بچه", 300, "🍼"),
        ("baby_diaper", "پوشک بچه", 500, "🖇️"),
        ("baby_food", "غذای کمکی", 700, "🥣"),
        ("baby_toy", "اسباب‌بازی", 1500, "🧸"),
    ],
    "shop_pet": [
        ("pet_cat", "گربه", 5000, "🐱"),
        ("pet_dog", "سگ", 8000, "🐶"),
        ("pet_rabbit", "خرگوش", 3000, "🐰"),
        ("pet_parrot", "طوطی", 10000, "🦜"),
    ],
    "shop_vehicle": [
        ("vehicle_bicycle", "دوچرخه", 10000, "🚲"),
        ("vehicle_motorcycle", "موتور", 50000, "🏍️"),
        ("vehicle_car", "ماشین", 200000, "🚗"),
        ("vehicle_airplane", "هواپیما", 1000000, "✈️"),
    ],
}


# -------------------- Main menu --------------------

def main_menu():
    return InlineKeyboardMarkup([
        [B("👤 پروفایل / موجودی", "profile", "primary")],
        [
            B("🛒 فروشگاه", "shop", "primary"),
            B("🏠 کسب درآمد", "income", "primary"),
        ],
        [
            B("🏦 بانک", "bank", "primary"),
            B("📈 ترید", "trade", "primary"),
        ],
        [
            B("💱 صرافی رمزارز", "crypto", "primary"),
            B("🏁 مسابقه / ماشین‌ها", "cars", "primary"),
        ],
        [
            B("🏴 بازار سیاه", "black_market", "primary"),
            B("📦 انبار و فروش", "inventory", "primary"),
        ],
        [B("🕸️ دارک وب", "dark_web", "primary")],
        [B("🏳️ کلن", "clan", "primary")],
        [B("❓ راهنما", "help", "primary")],
        [B("➕ افزودن ربات به گروه", "add_group", "success")],
    ])
def home_text(user):
    p = get_player(user)
    return (
        f"👋 سلام {p['name']}\n\n"
        f"💲 موجودی: $ {p['coins']:,}\n"
        f"🏦 بانک: $ {p['bank']:,}\n"
        f"🏷️ سطح: نوب\n\n"
        "از منوی زیر استفاده کن:"
    )
def back_menu():
    return InlineKeyboardMarkup([
        [B("منو اصلی", callback_data="home")]
    ])


# -------------------- Bank --------------------

def bank_text(user_id):
    p = get_player_raw(user_id)
    return (
        "🏦 بانک\n"
        "سود روزانه: 1%\n\n"
        f"💵 موجودی نقدی: $ {p['coins']:,}\n"
        f"🏦 موجودی بانک: $ {p['bank']:,}\n"
        f"📈 سود انباشته: $ {p['bank_profit']:,}\n"
        "💸 آماده برداشت"
    )


def bank_keyboard():
    return InlineKeyboardMarkup([
        [B("💰 سپرده 5,000", "bank_deposit:5000", "danger")],
        [B("💰 سپرده 50,000", "bank_deposit:50000", "danger")],
        [B("💰 سپرده 200,000", "bank_deposit:200000", "danger")],
        [B("💳 برداشت کامل", "bank_withdraw", "danger")],
        [B("🔙 برگشت", "home", "primary")],
    ])
def deposit_amount(user_id, amount):
    conn = db()
    row = conn.execute(
        "SELECT coins FROM players WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not row or row["coins"] < amount:
        conn.close()
        return False, "❌ موجودی نقدی کافی نیست."

    conn.execute(
        "UPDATE players SET coins=coins-?, bank=bank+? WHERE user_id=?",
        (amount, amount, user_id)
    )
    conn.commit()
    conn.close()
    return True, f"✅ {amount:,} $ به بانک سپرده شد."


def withdraw_bank(user_id):
    conn = db()
    row = conn.execute(
        "SELECT bank, bank_profit FROM players WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not row:
        conn.close()
        return "❌ بازیکن پیدا نشد."

    total = int(row["bank"]) + int(row["bank_profit"])
    if total <= 0:
        conn.close()
        return "❌ مبلغی برای برداشت وجود ندارد."

    conn.execute(
        """
        UPDATE players
        SET coins=coins+?, bank=0, bank_profit=0
        WHERE user_id=?
        """,
        (total, user_id)
    )
    conn.commit()
    conn.close()
    return f"✅ برداشت کامل انجام شد.\n💵 مبلغ دریافتی: $ {total:,}"


# -------------------- Income --------------------

# کسب‌وکارهای بخش «کسب درآمد» مطابق نمونه‌ای که کاربر فرستاد.
# درآمد پایه هر ۵ ساعت است و خریدها داخل SQLite ذخیره می‌شوند.
INCOME_ITEMS = [
    ("income_supermarket", "🏪 سوپرمارکت", 200000, 8000),
    ("income_restaurant", "🍽️ رستوران", 400000, 16000),
    ("income_bakery", "🥖 نانوایی", 700000, 28000),
    ("income_flour_farm", "🌾 مزرعه آرد", 1200000, 48000),
    ("income_factory", "🏭 کارخانه", 1800000, 74000),
    ("income_brothel", "🚫 جنده‌خونه", 2500000, 105000),
    ("income_iron_mine", "⛏️ معدن آهن", 3500000, 150000),
    ("income_opium_farm", "⭐ مزرعه تریاک", 5000000, 220000),
    ("income_falafel", "🥙 فلافلی Ocean", 7000000, 300000),
    ("income_akbar_jojeh", "🍗 اکبر جوجه", 13000000, 420000),
]
INCOME_PERIOD = 5 * 60 * 60
INCOME_CAPACITY = 9


def income_row(user_id, business_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM income_businesses WHERE user_id=? AND business_id=?",
        (user_id, business_id),
    ).fetchone()
    conn.close()
    return row


def income_owned_count(user_id):
    conn = db()
    row = conn.execute(
        "SELECT COALESCE(SUM(quantity),0) AS total FROM income_businesses WHERE user_id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    return int(row["total"] or 0)


def income_collectable(user_id):
    now = int(time.time())
    total = 0
    conn = db()
    rows = conn.execute(
        "SELECT quantity,income,last_income FROM income_businesses WHERE user_id=? AND quantity>0",
        (user_id,),
    ).fetchall()
    for row in rows:
        last = int(row["last_income"] or now)
        periods = max(0, (now - last) // INCOME_PERIOD)
        total += periods * int(row["income"]) * int(row["quantity"])
    conn.close()
    return total


def income_collect(user_id):
    now = int(time.time())
    total = 0
    conn = db()
    rows = conn.execute(
        "SELECT business_id,quantity,income,last_income FROM income_businesses WHERE user_id=? AND quantity>0",
        (user_id,),
    ).fetchall()
    for row in rows:
        last = int(row["last_income"] or now)
        periods = max(0, (now - last) // INCOME_PERIOD)
        if periods:
            total += periods * int(row["income"]) * int(row["quantity"])
            new_last = last + periods * INCOME_PERIOD
            conn.execute(
                "UPDATE income_businesses SET last_income=? WHERE user_id=? AND business_id=?",
                (new_last, user_id, row["business_id"]),
            )
    if total:
        conn.execute(
            "UPDATE players SET coins=coins+? WHERE user_id=?",
            (total, user_id),
        )
    conn.commit()
    conn.close()
    return total


def income_text(user_id):
    owned = income_owned_count(user_id)
    pending = income_collectable(user_id)
    return (
        "🏠 کسب درآمد\n\n"
        f"📦 تعداد کسب‌وکارهای تو: {owned} (ظرفیت {INCOME_CAPACITY})\n"
        f"💵 درآمد قابل برداشت: $ {pending:,}\n\n"
        "روی هر کسب‌وکار بزن تا جزئیاتش رو ببینی."
    )


def income_keyboard():
    rows = []
    for key, title, price, income in INCOME_ITEMS:
        rows.append([
            B(f"{title} — {price:,} $", key, "primary")
        ])
    rows.append([B("💰 برداشت درآمد", "income_collect", "success")])
    rows.append([B("🔙 برگشت", "home", "primary")])
    return InlineKeyboardMarkup(rows)


def income_detail_keyboard(business_id, can_buy=True):
    rows = []
    if can_buy:
        item = next(x for x in INCOME_ITEMS if x[0] == business_id)
        rows.append([B(f"💠 خرید ({item[2]:,})", f"income_buy:{business_id}", "success")])
    rows.append([B("برگشت 🔙", "income", "primary")])
    return InlineKeyboardMarkup(rows)


def income_detail_text(user_id, business_id):
    item = next((x for x in INCOME_ITEMS if x[0] == business_id), None)
    if not item:
        return "❌ این کسب‌وکار پیدا نشد."
    _, name, price, income = item
    row = income_row(user_id, business_id)
    quantity = int(row["quantity"]) if row else 0
    return (
        f"{name}\n\n"
        f"💵 قیمت خرید: $ {price:,}\n"
        f"📈 درآمد پایه هر ۵ ساعت (هر واحد): $ {income:,}\n"
        f"📦 تعداد شما: {quantity} (ظرفیت {INCOME_CAPACITY})\n"
        f"🧮 مجموع درآمد هر ۵ ساعت: $ {income * quantity:,}\n"
        f"💰 درآمد قابل برداشت: $ {income_collectable(user_id):,}"
    )


def buy_income_business(user_id, business_id):
    item = next((x for x in INCOME_ITEMS if x[0] == business_id), None)
    if not item:
        return "❌ این کسب‌وکار پیدا نشد."
    _, name, price, income = item
    conn = db()
    player = conn.execute(
        "SELECT coins FROM players WHERE user_id=?", (user_id,)
    ).fetchone()
    if not player:
        conn.close()
        return "❌ بازیکن پیدا نشد."
    row = conn.execute(
        "SELECT quantity FROM income_businesses WHERE user_id=? AND business_id=?",
        (user_id, business_id),
    ).fetchone()
    quantity = int(row["quantity"]) if row else 0
    if quantity >= INCOME_CAPACITY:
        conn.close()
        return f"❌ ظرفیت این کسب‌وکار پر است. ظرفیت: {INCOME_CAPACITY}"
    if int(player["coins"]) < price:
        conn.close()
        return f"❌ موجودی کافی نیست.\n💵 قیمت: $ {price:,}"

    now = int(time.time())
    conn.execute("UPDATE players SET coins=coins-? WHERE user_id=?", (price, user_id))
    if row:
        conn.execute(
            "UPDATE income_businesses SET quantity=quantity+1, last_income=? WHERE user_id=? AND business_id=?",
            (now, user_id, business_id),
        )
    else:
        conn.execute(
            "INSERT INTO income_businesses(user_id,business_id,business_name,price,income,quantity,last_income) VALUES(?,?,?,?,?,?,?)",
            (user_id, business_id, name, price, income, 1, now),
        )
    conn.commit()
    conn.close()
    return f"✅ {name} خریداری شد.\n💸 پرداخت: $ {price:,}\n📈 درآمد هر ۵ ساعت: $ {income:,}"


# -------------------- Trade --------------------

def trade_keyboard():
    return InlineKeyboardMarkup([
        [B("📈 ترید با 1,000", "trade:1000", "primary")],
        [B("📈 ترید با 10,000", "trade:10000", "primary")],
        [B("📈 ترید با 50,000", "trade:50000", "primary")],
        [B("📈 ترید با 100,000", "trade:100000", "primary")],
        [B("برگشت 🔙", "home", "primary")],
    ])
def run_trade(user_id, amount):
    conn = db()
    row = conn.execute(
        "SELECT coins FROM players WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not row or row["coins"] < amount:
        conn.close()
        return "❌ موجودی کافی نیست."

    # Simple 50/50 game mechanic; the screenshot only specifies the selectable stakes.
    if random.choice([True, False]):
        result = amount
        conn.execute(
            "UPDATE players SET coins=coins+? WHERE user_id=?",
            (result, user_id)
        )
        message = f"📈 سود کردی! +{result:,}"
    else:
        conn.execute(
            "UPDATE players SET coins=coins-? WHERE user_id=?",
            (amount, user_id)
        )
        message = f"📉 باختی! -{amount:,}"

    conn.commit()
    conn.close()
    return message


# -------------------- Cars --------------------

def cars_text():
    lines = [
        "🏁 ماشین‌ها و مسابقه\n\n",
        "ماشین‌های تو:\n",
        "—\n\n",
        "برای شروع مسابقه توی گروه بنویس: مسابقه 5000"
    ]
    return "\n".join(lines)


def cars_keyboard():
    rows = []
    for car_id, name, price in CARS:
        rows.append([
            B(f"🚗 خرید {name} — {price:,}", f"car:{car_id}", "success")
        ])
    rows.append([B("منو 🔙", "home", "primary")])
    return InlineKeyboardMarkup(rows)
def buy_car(user_id, car_id):
    selected = next((c for c in CARS if c[0] == car_id), None)
    if not selected:
        return "❌ ماشین پیدا نشد."

    _, name, price = selected
    conn = db()
    row = conn.execute(
        "SELECT coins FROM players WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not row or row["coins"] < price:
        conn.close()
        return "❌ موجودی کافی نیست."

    owned = conn.execute(
        "SELECT 1 FROM cars WHERE user_id=? AND car_id=?",
        (user_id, car_id)
    ).fetchone()

    if owned:
        conn.close()
        return "ℹ️ این ماشین را قبلاً خریدی."

    conn.execute(
        "UPDATE players SET coins=coins-? WHERE user_id=?",
        (price, user_id)
    )
    conn.execute(
        "INSERT INTO cars(user_id,car_id,car_name,price) VALUES(?,?,?,?)",
        (user_id, car_id, name, price)
    )
    conn.execute(
        """
        INSERT INTO inventory(user_id,item_id,item_name,quantity)
        VALUES(?,?,?,1)
        ON CONFLICT(user_id,item_id)
        DO UPDATE SET quantity=quantity+1
        """,
        (user_id, f"CAR_{car_id}", f"🚗 {name}")
    )
    conn.commit()
    conn.close()

    return f"✅ {name} خریداری شد و به انبار اضافه شد.\n💸 قیمت: {price:,} $"


# -------------------- Crypto exchange --------------------

def crypto_text(user_id):
    lines = [
        "💱 صرافی رمزارز",
        "برای مقدار دلخواه بنویس: خرید 0.5 بیتکوین یا فروش OCEAN 12",
        "",
    ]
    for symbol, price in CRYPTO.items():
        lines.append(
            f"• {symbol} ({CRYPTO_NAMES[symbol]}) — {price:g} 💲"
        )
    return "\n".join(lines)


def crypto_keyboard():
    rows = []
    for symbol in CRYPTO:
        rows.append([
            B(f"💲 خرید {symbol}", f"crypto_buy:{symbol}", "success"),
            B(f"💷 فروش {symbol}", f"crypto_sell:{symbol}", "primary"),
        ])
    rows.append([B("برگشت 🔙", "home", "primary")])
    return InlineKeyboardMarkup(rows)
def crypto_trade(user_id, symbol, quantity, side):
    symbol = symbol.upper()
    if symbol not in CRYPTO:
        return "❌ رمزارز پیدا نشد."

    try:
        quantity = float(quantity)
    except ValueError:
        return "❌ مقدار نامعتبر است."

    if quantity <= 0:
        return "❌ مقدار باید بیشتر از صفر باشد."

    price = CRYPTO[symbol]
    total = quantity * price

    conn = db()
    player = conn.execute(
        "SELECT coins FROM players WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if side == "buy":
        if not player or player["coins"] < total:
            conn.close()
            return "❌ موجودی کافی نیست."

        conn.execute(
            "UPDATE players SET coins=coins-? WHERE user_id=?",
            (int(total), user_id)
        )
        conn.execute(
            """
            INSERT INTO crypto(user_id,symbol,quantity)
            VALUES(?,?,?)
            ON CONFLICT(user_id,symbol)
            DO UPDATE SET quantity=quantity+excluded.quantity
            """,
            (user_id, symbol, quantity)
        )
        conn.commit()
        conn.close()
        return f"✅ خرید انجام شد.\n{quantity:g} {symbol}\n💸 هزینه: {total:,.3f} $"

    holding = conn.execute(
        "SELECT quantity FROM crypto WHERE user_id=? AND symbol=?",
        (user_id, symbol)
    ).fetchone()

    if not holding or holding["quantity"] + 1e-12 < quantity:
        conn.close()
        return "❌ مقدار کافی از این رمزارز در دارایی شما نیست."

    conn.execute(
        "UPDATE players SET coins=coins+? WHERE user_id=?",
        (int(total), user_id)
    )
    new_qty = holding["quantity"] - quantity
    conn.execute(
        "UPDATE crypto SET quantity=? WHERE user_id=? AND symbol=?",
        (max(0, new_qty), user_id, symbol)
    )
    conn.commit()
    conn.close()
    return f"✅ فروش انجام شد.\n{quantity:g} {symbol}\n💵 دریافتی: {total:,.3f} $"


# -------------------- Inventory --------------------

def inventory_text(user_id):
    conn = db()
    rows = conn.execute(
        """
        SELECT item_id, item_name, quantity
        FROM inventory
        WHERE user_id=? AND quantity>0
        ORDER BY rowid
        """,
        (user_id,)
    ).fetchall()
    conn.close()

    if not rows:
        return (
            "📦 انبار\n\n"
            "انبار خالی است.\n\n"
            "آیتم‌هایی که از فروشگاه یا بازار سیاه بخری اینجا اضافه می‌شوند."
        )

    lines = ["📦 انبار\n"]
    for row in rows:
        lines.append(
            f"• {row['item_name']} ×{row['quantity']}  [{row['item_id']}]"
        )
    lines += [
        "",
        "فروش به ربات: فروش <id>",
        "مثال: فروش SW001",
    ]
    return "\n".join(lines)


def inventory_keyboard():
    return InlineKeyboardMarkup([
        [B("💵 فروش آیتم", callback_data="inventory_sell_help")],
        [B("🔙 برگشت", callback_data="home")],
    ])


def sell_inventory_item(user_id, item_id):
    item_id = item_id.upper()
    conn = db()
    row = conn.execute(
        """
        SELECT item_name, quantity
        FROM inventory
        WHERE user_id=? AND item_id=? AND quantity>0
        """,
        (user_id, item_id)
    ).fetchone()

    if not row:
        conn.close()
        return "❌ این آیتم در انبار شما پیدا نشد."

    # Inventory sale uses half of the displayed black-market/store purchase price when known.
    price = 1000
    for iid, _, p, _ in BLACK_MARKET:
        if iid == item_id:
            price = p // 2
            break

    conn.execute(
        "UPDATE inventory SET quantity=quantity-1 WHERE user_id=? AND item_id=?",
        (user_id, item_id)
    )
    conn.execute(
        "UPDATE players SET coins=coins+? WHERE user_id=?",
        (price, user_id)
    )
    conn.commit()
    conn.close()

    return f"✅ {row['item_name']} فروخته شد.\n💵 دریافتی: {price:,} $"


# -------------------- Store purchases --------------------

def buy_shop_item(user_id, category, item_id):
    selected = next(
        (item for item in SHOP_ITEMS.get(category, []) if item[0] == item_id),
        None,
    )
    if not selected:
        return "❌ این کالا پیدا نشد."

    _, name, price, emoji = selected
    conn = db()
    row = conn.execute(
        "SELECT coins FROM players WHERE user_id=?",
        (user_id,),
    ).fetchone()

    if not row or row["coins"] < price:
        conn.close()
        return f"❌ موجودی کافی نیست.\n💵 قیمت: {price:,} $"

    conn.execute(
        "UPDATE players SET coins=coins-? WHERE user_id=?",
        (price, user_id),
    )
    conn.execute(
        """
        INSERT INTO inventory(user_id,item_id,item_name,quantity)
        VALUES(?,?,?,1)
        ON CONFLICT(user_id,item_id)
        DO UPDATE SET quantity=quantity+1
        """,
        (user_id, item_id.upper(), f"{emoji} {name}"),
    )
    conn.commit()
    conn.close()

    return f"✅ {name} خریداری شد.\n💸 قیمت: {price:,} $"


def shop_category_keyboard(category):
    rows = []
    for item_id, name, price, emoji in SHOP_ITEMS[category]:
        rows.append([
            B(f"{emoji} 💵 {price:,} — {name}", f"shopbuy:{category}:{item_id}", "primary")
        ])
    rows.append([B("برگشت 🔙", "shop", "primary")])
    return InlineKeyboardMarkup(rows)


# -------------------- Black market --------------------

def black_market_text():
    return (
        "🏴 بازار سیاه — 64 آیتم\n\n"
        "برای سرج بنویس: سرچ شمشیر\n"
        "خرید با کد: SW001"
    )


def black_market_keyboard():
    rows = []
    for item_id, name, price, emoji in BLACK_MARKET:
        style = "danger" if item_id == "MUG01" else "primary"
        rows.append([
            B(f"{emoji} 💵 {price:,} — {name}", f"blackbuy:{item_id}", style)
        ])
    rows.append([B("منو 🔙", "home", "primary")])
    return InlineKeyboardMarkup(rows)
def buy_black_market(user_id, item_id):
    selected = next((x for x in BLACK_MARKET if x[0] == item_id), None)
    if not selected:
        return "❌ آیتم پیدا نشد."

    item_id, name, price, emoji = selected

    conn = db()
    row = conn.execute(
        "SELECT coins FROM players WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not row or row["coins"] < price:
        conn.close()
        return "❌ موجودی کافی نیست."

    conn.execute(
        "UPDATE players SET coins=coins-? WHERE user_id=?",
        (price, user_id)
    )
    conn.execute(
        """
        INSERT INTO inventory(user_id,item_id,item_name,quantity)
        VALUES(?,?,?,1)
        ON CONFLICT(user_id,item_id)
        DO UPDATE SET quantity=quantity+1
        """,
        (user_id, item_id, f"{emoji} {name}")
    )
    conn.commit()
    conn.close()

    return f"✅ {name} خریداری شد.\n📦 به انبار اضافه شد.\n💸 قیمت: {price:,} $"


# -------------------- Dark web --------------------

def dark_web_text():
    return (
        "دارک وب 🕸️\n\n"
        "برای استفاده توی گروه روی پیام طرف ریپلای کن و بنویس:\n"
        "• اجیر قاتل — هزینه: $10,000 (از موجودی)\n"
        "• اجیر هکر — هزینه: $20,000 (از بانک)\n\n"
        "هر دو 30٪ شانس لو رفتن و جریمه دارن. اگه طرف بیمه باشه فقط 10٪ برداشت میشه."
    )


def dark_web_keyboard():
    return InlineKeyboardMarkup([
        [B("منو 🔙", "home", "primary")],
    ])
# -------------------- Clan --------------------

def clan_text():
    return (
        "🏳️ راهنمای کلن\n"
        "• ساخت کلن <اسم> — $40,000\n"
        "• جوین <اسم کلن> — درخواست عضویت\n"
        "• کلن <اسم> — کارت کلن (رهبر/معاون: مدیریت اعضا و خزانه)\n"
        "• واریز کلن <مبلغ> / برداشت کلن <مبلغ>\n"
        "• چالش کلن — پله‌های امتیاز و جایزه‌ها\n"
        "• اعلام جنگ کلن <اسم کلن> — فقط رهبر/معاون\n"
        "• حمله / دفاع — هر ۲۵ دقیقه یک بار\n"
        "• رتبه کلن‌ها — جدول جهانی\n"
        "• خروج از کلن / انحلال کلن"
    )


def clan_keyboard():
    return InlineKeyboardMarkup([
        [B("منو 🔙", "home", "primary")],
    ])
# -------------------- Help --------------------

def help_text():
    return (
        "💾 راهنمای ربات آقایون\n\n"
        "روی هر دسته بزن تا دستوراتش رو ببینی."
    )


def help_keyboard():
    return InlineKeyboardMarkup([
        [
            B("🏳️ کلن", "help_clan", "primary"),
            B("💲 درآمد رایگان", "help_income", "primary"),
        ],
        [
            B("🎮 بازی‌ها", "help_games", "primary"),
            B("💰 پول و بانک", "help_money", "primary"),
        ],
        [
            B("🏠 سرمایه‌گذاری", "help_invest", "primary"),
            B("🛒 فروشگاه و بازار", "help_store", "primary"),
        ],
        [
            B("💜 اجتماعی و خانواده", "help_social", "primary"),
            B("🥷 دزدی و دارک وب", "help_crime", "primary"),
        ],
        [
            B("🚀 موشک", "help_rocket", "primary"),
            B("🏆 سایر", "help_other", "primary"),
        ],
        [B("منو اصلی 🔙", "home", "primary")],
    ])
HELP_DETAILS = {
    "help_clan": "🏳️ کلن\nساخت کلن، جوین، کارت کلن، خزانه، چالش، جنگ، رتبه و خروج.",
    "help_income": "💲 درآمد رایگان\nبخش کسب درآمد و جمع‌آوری درآمد.",
    "help_games": "🎮 بازی‌ها\nبازی‌ها و سرگرمی‌های داخل OceanGame.",
    "help_money": "💰 پول و بانک\nموجودی، سپرده، برداشت و سود بانک.",
    "help_invest": "🏠 سرمایه‌گذاری\nبخش سرمایه‌گذاری و مدیریت دارایی.",
    "help_store": "🛒 فروشگاه و بازار\nخرید آیتم‌ها و انتقال آن‌ها به انبار.",
    "help_social": "💜 اجتماعی و خانواده\nامکانات اجتماعی بازی.",
    "help_crime": "🥷 دزدی و دارک وب\nدستورات مربوط به بخش دارک وب بازی.",
    "help_rocket": "🚀 موشک\nبخش موشک.",
    "help_other": "🏆 سایر\nسایر امکانات ربات.",
}


# -------------------- Callback handler --------------------

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
            f"👤 {p['name']}\n"
            f"💵 موجودی: $ {p['coins']:,}\n"
            f"🏦 بانک: $ {p['bank']:,}\n"
            f"💰 مجموع: $ {p['coins'] + p['bank']:,}\n"
            f"🏷️ سطح: نوب (لول {p['level']})"
        )
        await q.edit_message_text(text, reply_markup=back_menu())
        return

    if data == "bank":
        await q.edit_message_text(bank_text(user.id), reply_markup=bank_keyboard())
        return

    if data.startswith("bank_deposit:"):
        amount = int(data.split(":")[1])
        ok, message = deposit_amount(user.id, amount)
        await q.answer(message, show_alert=True)
        await q.edit_message_text(bank_text(user.id), reply_markup=bank_keyboard())
        return

    if data == "bank_withdraw":
        message = withdraw_bank(user.id)
        await q.answer(message, show_alert=True)
        await q.edit_message_text(bank_text(user.id), reply_markup=bank_keyboard())
        return

    if data == "income":
        await q.edit_message_text(
            income_text(user.id),
            reply_markup=income_keyboard()
        )
        return

    if data == "income_collect":
        amount = income_collect(user.id)
        if amount:
            message = f"✅ درآمد برداشت شد.\n💰 مبلغ دریافتی: $ {amount:,}"
        else:
            message = "ℹ️ فعلاً درآمدی برای برداشت آماده نیست.\n⏱️ هر ۵ ساعت درآمد جدید محاسبه می‌شود."
        await q.answer(message, show_alert=True)
        await q.edit_message_text(
            income_text(user.id),
            reply_markup=income_keyboard()
        )
        return

    if data.startswith("income_buy:"):
        business_id = data.split(":", 1)[1]
        message = buy_income_business(user.id, business_id)
        await q.answer(message, show_alert=True)
        await q.edit_message_text(
            income_detail_text(user.id, business_id),
            reply_markup=income_detail_keyboard(
                business_id,
                income_owned_count(user.id) < INCOME_CAPACITY
            )
        )
        return

    if data.startswith("income_"):
        business_id = data
        if any(x[0] == business_id for x in INCOME_ITEMS):
            await q.edit_message_text(
                income_detail_text(user.id, business_id),
                reply_markup=income_detail_keyboard(
                    business_id,
                    income_owned_count(user.id) < INCOME_CAPACITY
                )
            )
        else:
            await q.answer("❌ این گزینه پیدا نشد.", show_alert=True)
        return

    if data == "trade":
        text = (
            "📈 ترید\n"
            "مبلغ شرط رو انتخاب کن. بازار پرریسکه.\n"
            "میتونی توی گروه هم بنویسی: ترید 1000"
        )
        await q.edit_message_text(text, reply_markup=trade_keyboard())
        return

    if data.startswith("trade:"):
        amount = int(data.split(":")[1])
        message = run_trade(user.id, amount)
        await q.answer(message, show_alert=True)
        await q.edit_message_text(
            "📈 ترید\n\nمبلغ شرط رو انتخاب کن.",
            reply_markup=trade_keyboard()
        )
        return

    if data == "cars":
        await q.edit_message_text(cars_text(), reply_markup=cars_keyboard())
        return

    if data.startswith("car:"):
        message = buy_car(user.id, data.split(":")[1])
        await q.answer(message, show_alert=True)
        await q.edit_message_text(cars_text(), reply_markup=cars_keyboard())
        return

    if data == "crypto":
        await q.edit_message_text(
            crypto_text(user.id),
            reply_markup=crypto_keyboard()
        )
        return

    if data.startswith("crypto_buy:") or data.startswith("crypto_sell:"):
        side, symbol = data.split(":")
        price = CRYPTO[symbol]
        if side == "crypto_buy":
            message = (
                f"💵 خرید {symbol}\n"
                f"قیمت فعلی: {price:g} $\n\n"
                f"برای مقدار دلخواه بنویس: خرید 0.5 {CRYPTO_NAMES[symbol]}"
            )
        else:
            message = (
                f"💷 فروش {symbol}\n"
                f"قیمت فعلی: {price:g} $\n\n"
                f"برای مقدار دلخواه بنویس: فروش {symbol} 12"
            )
        await q.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [B("🔙 برگشت به صرافی", callback_data="crypto")]
            ])
        )
        return

    if data == "inventory":
        await q.edit_message_text(
            inventory_text(user.id),
            reply_markup=inventory_keyboard()
        )
        return

    if data == "inventory_sell_help":
        await q.edit_message_text(
            "📦 فروش آیتم\n\n"
            "فرمت: فروش <id>\n"
            "مثال: فروش SW001",
            reply_markup=InlineKeyboardMarkup([
                [B("🔙 برگشت به انبار", callback_data="inventory")]
            ])
        )
        return

    if data == "shop":
        await q.edit_message_text(
            "🛒 فروشگاه\n\nچی میخوای بخری؟",
            reply_markup=InlineKeyboardMarkup([
                [B("🐾 پت", callback_data="shop_pet")],
                [B("🚘 وسیله نقلیه", callback_data="shop_vehicle")],
                [B("🍼 لوازم بچه", callback_data="shop_baby")],
                [B("🔙 برگشت", callback_data="home")],
            ])
        )
        return

    if data in ("shop_pet", "shop_vehicle", "shop_baby"):
        titles = {
            "shop_pet": "🐾 پت",
            "shop_vehicle": "🚘 وسیله نقلیه",
            "shop_baby": "🍼 لوازم بچه",
        }
        await q.edit_message_text(
            f"{titles[data]}\n\n"
            "برای خرید روی گزینه موردنظر بزن:",
            reply_markup=shop_category_keyboard(data)
        )
        return

    if data.startswith("shopbuy:"):
        parts = data.split(":", 2)
        if len(parts) == 3:
            category, item_id = parts[1], parts[2]
            message = buy_shop_item(user.id, category, item_id)
            await q.answer(message, show_alert=True)
            titles = {
                "shop_pet": "🐾 پت",
                "shop_vehicle": "🚘 وسیله نقلیه",
                "shop_baby": "🍼 لوازم بچه",
            }
            await q.edit_message_text(
                f"{titles.get(category, '🛒 فروشگاه')}\n\n"
                "برای خرید روی گزینه موردنظر بزن:",
                reply_markup=shop_category_keyboard(category)
            )
            return

    if data == "pets":
        await q.edit_message_text(
            "🐾 پت و لوازم\n\nپت‌ها و لوازم جانبی در این بخش قرار می‌گیرند.",
            reply_markup=back_menu()
        )
        return

    if data == "black_market":
        await q.edit_message_text(
            black_market_text(),
            reply_markup=black_market_keyboard()
        )
        return

    if data.startswith("blackbuy:"):
        message = buy_black_market(user.id, data.split(":")[1])
        await q.answer(message, show_alert=True)
        await q.edit_message_text(
            black_market_text(),
            reply_markup=black_market_keyboard()
        )
        return

    if data == "dark_web":
        await q.edit_message_text(
            dark_web_text(),
            reply_markup=dark_web_keyboard()
        )
        return

    if data in ("dark_assassin", "dark_hacker"):
        if data == "dark_assassin":
            text = "🔪 اجیر قاتل\nبرای استفاده، روی پیام طرف ریپلای کن و دستور مربوطه را بفرست."
        else:
            text = "💻 اجیر هکر\nبرای استفاده، روی پیام طرف ریپلای کن و دستور مربوطه را بفرست."
        await q.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [B("🔙 برگشت به دارک وب", callback_data="dark_web")]
            ])
        )
        return

    if data == "clan":
        await q.edit_message_text(clan_text(), reply_markup=clan_keyboard())
        return

    if data.startswith("clan_") and data != "clan":
        await q.answer("این گزینه فعلاً به‌صورت راهنمای کلن نمایش داده می‌شود.", show_alert=True)
        await q.edit_message_text(clan_text(), reply_markup=clan_keyboard())
        return

    if data == "help":
        await q.edit_message_text(help_text(), reply_markup=help_keyboard())
        return

    if data in HELP_DETAILS:
        await q.edit_message_text(
            HELP_DETAILS[data],
            reply_markup=InlineKeyboardMarkup([
                [B("🔙 برگشت به راهنما", callback_data="help")]
            ])
        )
        return

    if data == "add_group":
        await q.edit_message_text(
            "➕ افزودن ربات به گروه\n\n"
            "ربات را به گروه موردنظر اضافه کن و دسترسی‌های لازم را بده.",
            reply_markup=back_menu()
        )
        return

    await q.edit_message_text(
        "این بخش هنوز فعال نشده است.",
        reply_markup=back_menu()
    )


# -------------------- Text commands --------------------

def normalize_digits(value):
    table = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    return value.translate(table)


def parse_crypto_name(value):
    value = value.strip().upper()
    if value in CRYPTO:
        return value
    for symbol, name in CRYPTO_NAMES.items():
        if value == name.upper():
            return symbol
    return None



def rob_replied_user(thief_user, target_user):
    """Steal 10% of the replied user's cash; 70% success / 30% caught."""
    if not target_user:
        return "❌ باید روی پیام یک کاربر ریپلای کنی و بنویسی: دزدی"

    if thief_user.id == target_user.id:
        return "❌ نمی‌تونی از خودت دزدی کنی."

    conn = db()
    try:
        thief = conn.execute(
            "SELECT coins, name FROM players WHERE user_id=?",
            (thief_user.id,)
        ).fetchone()
        target = conn.execute(
            "SELECT coins, name FROM players WHERE user_id=?",
            (target_user.id,)
        ).fetchone()

        if thief is None:
            conn.execute(
                """
                INSERT INTO players(
                    user_id, name, coins, bank, level,
                    bank_profit, bank_last_day, created_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (thief_user.id, thief_user.first_name or "بازیکن", 0, 0, 1, 0,
                 int(time.time() // 86400), int(time.time()))
            )
            thief = conn.execute(
                "SELECT coins, name FROM players WHERE user_id=?",
                (thief_user.id,)
            ).fetchone()

        if target is None:
            conn.execute(
                """
                INSERT INTO players(
                    user_id, name, coins, bank, level,
                    bank_profit, bank_last_day, created_at
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (target_user.id, target_user.first_name or "بازیکن", 0, 0, 1, 0,
                 int(time.time() // 86400), int(time.time()))
            )
            target = conn.execute(
                "SELECT coins, name FROM players WHERE user_id=?",
                (target_user.id,)
            ).fetchone()

        thief_name = thief["name"]
        target_name = target["name"]
        thief_coins = int(thief["coins"])
        target_coins = int(target["coins"])

        if target_coins <= 0:
            conn.commit()
            return f"❌ {target_name} موجودی نقدی ندارد."

        if random.random() < 0.70:
            stolen = max(1, int(target_coins * 0.10))
            conn.execute(
                "UPDATE players SET coins=coins-? WHERE user_id=?",
                (stolen, target_user.id)
            )
            conn.execute(
                "UPDATE players SET coins=coins+? WHERE user_id=?",
                (stolen, thief_user.id)
            )
            conn.commit()
            return f"🤑 {thief_name} موقع دزدیدن از {target_name} موفق شد و ${stolen:,} دزدید!"

        fine = min(max(10, int(thief_coins * 0.10)), thief_coins)
        if fine > 0:
            conn.execute(
                "UPDATE players SET coins=coins-? WHERE user_id=?",
                (fine, thief_user.id)
            )
        conn.commit()
        return f"🚓 گیر {thief_name} موقع دزدیدن از {target_name} ! ${fine:,} جریمه افتاد و"
    finally:
        conn.close()


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    raw = update.message.text.strip()
    text = normalize_digits(raw)
    user = update.effective_user

    if text in {"منو", "مانی", "/menu"}:
        # متن «منو» دقیقاً همان عملکرد /start را اجرا می‌کند.
        await start(update, context)
        return

    if text == "دزدی":
        replied = update.message.reply_to_message
        target_user = replied.from_user if replied and replied.from_user else None
        await update.message.reply_text(rob_replied_user(user, target_user))
        return

    if text in {"کسب درآمد", "کسب درآمدها"}:
        await update.message.reply_text(
            income_text(user.id),
            reply_markup=income_keyboard()
        )
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
            await update.message.reply_text(
                "❌ فرمت درست: سپرده + مبلغ\nمثال: سپرده 500"
            )
            return

        amount = int(parts[1])
        if amount <= 0:
            await update.message.reply_text("❌ مبلغ باید بیشتر از صفر باشد.")
            return

        ok, message = deposit_amount(user.id, amount)
        await update.message.reply_text(message)
        return

    # Trade command: ترید 1000
    if text.startswith("ترید "):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            message = run_trade(user.id, int(parts[1]))
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ فرمت: ترید + مبلغ\nمثال: ترید 1000")
        return

    # Crypto buy command: خرید 0.5 بیتکوین
    if text.startswith("خرید "):
        parts = text.split(maxsplit=2)
        if len(parts) == 3:
            try:
                quantity = float(parts[1])
                symbol = parse_crypto_name(parts[2])
                if symbol:
                    await update.message.reply_text(
                        crypto_trade(user.id, symbol, quantity, "buy")
                    )
                    return
            except ValueError:
                pass

    # Crypto sell command: فروش OCEAN 12
    if text.startswith("فروش "):
        parts = text.split(maxsplit=2)
        if len(parts) == 3:
            symbol = parse_crypto_name(parts[1])
            try:
                quantity = float(parts[2])
            except ValueError:
                quantity = -1

            if symbol and quantity > 0:
                await update.message.reply_text(
                    crypto_trade(user.id, symbol, quantity, "sell")
                )
                return

        # Inventory sale: فروش SW001
        parts = text.split()
        if len(parts) == 2:
            await update.message.reply_text(
                sell_inventory_item(user.id, parts[1])
            )
            return

    # Black-market search command from the screenshot.
    if text.startswith("سرچ "):
        query = text[5:].strip()
        matches = [
            x for x in BLACK_MARKET
            if query in x[1] or query.upper() in x[0]
        ]
        if matches:
            lines = ["🏴 نتیجه سرچ:\n"]
            for item_id, name, price, emoji in matches:
                lines.append(f"{emoji} {name} — {price:,} $ [{item_id}]")
            await update.message.reply_text("\n".join(lines))
        else:
            await update.message.reply_text("❌ موردی پیدا نشد.")
        return

    # Black-market direct purchase: خرید با کد SW001
    if text.startswith("خرید با کد "):
        item_id = text.replace("خرید با کد ", "", 1).strip().upper()
        await update.message.reply_text(buy_black_market(user.id, item_id))
        return

    await update.message.reply_text(
        "دستور را نشناختم. برای دیدن منوی OceanGame بنویس: منو",
        reply_markup=main_menu()
    )


# -------------------- Start --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        home_text(update.effective_user),
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
