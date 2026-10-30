import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart

# ТОКЕН БОТА (Тестовый токен, указанный вами)
BOT_TOKEN = "9049984477:AAE2gpZbVwbGIdIY7SLktuc0Ssu45oAViSU"
# ИД создателя для доступа к админ-панели
CREATOR_TELEGRAM_ID = 9215022914

# --- БАЗА ДАННЫХ (SQLite) ---
DB_NAME = "boxing_life.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            path_type TEXT DEFAULT 'legal',
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            health INTEGER DEFAULT 100,
            max_health INTEGER DEFAULT 100,
            stamina INTEGER DEFAULT 100,
            max_stamina INTEGER DEFAULT 100,
            balance_dollars REAL DEFAULT 500.0,
            balance_coins INTEGER DEFAULT 0,
            balance_diamonds INTEGER DEFAULT 0,
            title TEXT DEFAULT 'Новичок',
            strength INTEGER DEFAULT 10,
            speed INTEGER DEFAULT 10,
            endurance INTEGER DEFAULT 10,
            defense INTEGER DEFAULT 10,
            reaction INTEGER DEFAULT 10,
            accuracy INTEGER DEFAULT 10,
            crit INTEGER DEFAULT 5,
            recovery INTEGER DEFAULT 10,
            is_banned INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_NAME)

# --- ИГРОВЫЕ ДАННЫЕ NPC ---
NPCS = {
    1: {"name": "Артём «Малыш» Волков", "level": 1, "health": 100, "strength": 8},
    2: {"name": "Тимур «Быстрый» Садыков", "level": 3, "health": 120, "strength": 12},
    3: {"name": "Денис «Кулак» Морозов", "level": 5, "health": 150, "strength": 15},
    4: {"name": "Илья «Таран» Ковалёв", "level": 7, "health": 180, "strength": 18},
    5: {"name": "Рустам «Зверь» Алиев", "level": 10, "health": 220, "strength": 22},
}

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile"), InlineKeyboardButton(text="🥊 Бой с NPC", callback_data="menu_npcs")],
        [InlineKeyboardButton(text="🏋️ Тренировка", callback_data="menu_train"), InlineKeyboardButton(text="📊 Характеристики", callback_data="menu_stats")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="menu_shop"), InlineKeyboardButton(text="🎒 Инвентарь", callback_data="menu_inv")],
        [InlineKeyboardButton(text="⚙️ Помощь", callback_data="menu_help")]
    ])

# --- КОМАНДЫ СТАРТА И РЕГИСТРАЦИИ ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥊 Легальный бокс", callback_data="path_legal")],
        [InlineKeyboardButton(text="🩸 Бокс без правил", callback_data="path_street")]
    ])
    await message.answer(
        "🥊 **ДОБРО ПОЖАЛОВАТЬ В BOXING LIFE** 🥊\n\n"
        "Выберите свой путь в мире бокса:\n\n"
        "• **Легальный бокс**: Чемпионские пояса и официальные лиги.\n"
        "• **Бокс без правил**: Подпольные бои и уличные авторитеты.\n\n"
        "Сделайте свой выбор:",
        reply_markup=keyboard, parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("path_"))
async def set_path(callback: CallbackQuery):
    path_type = callback.data.split("_")[1]
    user = callback.from_user
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (user.id,))
    existing = cursor.fetchone()
    
    title = "Новичок" if path_type == "legal" else "Уличный новичок"
    
    if not existing:
        cursor.execute(
            "INSERT INTO users (telegram_id, username, path_type, title) VALUES (?, ?, ?, ?)",
            (user.id, user.username, path_type, title)
        )
        conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        f"✅ Вы успешно зарегистрированы! Путь выбран: **{'Легальный бокс' if path_type == 'legal' else 'Бокс без правил'}**.\n\n"
        "Главное меню игры:",
        reply_markup=get_main_menu(), parse_mode="Markdown"
    )

# --- ТЕКСТОВЫЕ КОМАНДЫ (БЕЗ слэша) ---
@dp.message(F.text.casefold() == "меню")
async def cmd_menu(message: Message):
    await message.answer("🏠 **Главное меню BOXING LIFE:**", reply_markup=get_main_menu(), parse_mode="Markdown")

@dp.message(F.text.casefold() == "профиль")
async def cmd_profile(message: Message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT path_type, level, exp, health, max_health, balance_dollars, title FROM users WHERE telegram_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        await message.answer("❌ Вы не зарегистрированы! Напишите /start")
        return
        
    path, lvl, exp, hp, max_hp, bal, title = row
    text = (
        f"👤 **ПРОФИЛЬ БОЙЦА**\n\n"
        f"🏆 Титул: {title}\n"
        f"⭐ Уровень: {lvl} (Опыт: {exp})\n"
        f"❤️ Здоровье: {hp}/{max_hp}\n"
        f"💰 Баланс: ${bal:.1f}\n"
        f"🥊 Путь: {'Легальный бокс' if path == 'legal' else 'Без правил'}"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text.casefold() == "админ панель")
async def cmd_admin(message: Message):
    if message.from_user.id != CREATOR_TELEGRAM_ID:
        await message.answer("❌ У вас нет прав администратора.")
        return
    await message.answer("⚙️ **Панель администратора BOXING LIFE**\nДоступные функции активны.", parse_mode="Markdown")

# --- ОБРАБОТЧИК КНОПОК МЕНЮ ---
@dp.callback_query(F.data.startswith("menu_"))
async def menu_handler(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    if action == "profile":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT path_type, level, exp, health, max_health, balance_dollars, title FROM users WHERE telegram_id = ?", (callback.from_user.id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            path, lvl, exp, hp, max_hp, bal, title = row
            await callback.message.edit_text(
                f"👤 **ПРОФИЛЬ БОЙЦА**\n\n🏆 Титул: {title}\n⭐ Уровень: {lvl}\n❤️ Здоровье: {hp}/{max_hp}\n💰 Баланс: ${bal:.1f}",
                reply_markup=get_main_menu(), parse_mode="Markdown"
            )
    elif action == "npcs":
        await callback.message.edit_text("🥊 **Каталог противников NPC:**\n1. Артём «Малыш» Волков (Ур. 1)\n2. Тимур «Быстрый» Садыков (Ур. 3)\n3. Денис «Кулак» Морозов (Ур. 5)", reply_markup=get_main_menu(), parse_mode="Markdown")
    elif action == "train":
        await callback.message.edit_text("🏋️ Вы начали тренировку на груше! Характеристики улучшены.", reply_markup=get_main_menu(), parse_mode="Markdown")
    elif action == "shop":
        await callback.message.edit_text("🛒 Магазин пуст или в разработке.", reply_markup=get_main_menu(), parse_mode="Markdown")
    elif action == "inv":
        await callback.message.edit_text("🎒 Ваш инвентарь пуст.", reply_markup=get_main_menu(), parse_mode="Markdown")
    elif action == "stats":
        await callback.message.edit_text("📊 Ваши характеристики в норме.", reply_markup=get_main_menu(), parse_mode="Markdown")
    elif action == "help":
        await callback.message.edit_text("ℹ️ Команды игры:\n• `профиль`\n• `меню`\n• `админ панель`", reply_markup=get_main_menu(), parse_mode="Markdown")

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🥊 Бот BOXING LIFE запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
