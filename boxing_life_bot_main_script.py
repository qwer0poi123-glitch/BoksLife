import asyncio
import logging
import random
import sqlite3
from typing import List, Tuple, Dict, Any

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Message,
    CallbackQuery,
)

# =====================================================================
# CONFIGURATION
# =====================================================================
BOT_TOKEN = "9049984477:AAE2gpZbVwbGIdIY7SLktuc0Ssu45oAViSU"
CREATOR_ID = 9215022914
DB_NAME = "boxing_life.db"

logging.basicConfig(level=logging.INFO)

# =====================================================================
# DATABASE SETUP & HELPERS
# =====================================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            path TEXT,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            health INTEGER DEFAULT 100,
            max_health INTEGER DEFAULT 100,
            stamina INTEGER DEFAULT 100,
            max_stamina INTEGER DEFAULT 100,
            dollars REAL DEFAULT 500.0,
            coins INTEGER DEFAULT 0,
            diamonds INTEGER DEFAULT 0,
            title TEXT,
            reborns INTEGER DEFAULT 0,
            strength INTEGER DEFAULT 10,
            speed INTEGER DEFAULT 10,
            endurance INTEGER DEFAULT 10,
            defense INTEGER DEFAULT 10,
            reaction INTEGER DEFAULT 10,
            accuracy INTEGER DEFAULT 10,
            crit INTEGER DEFAULT 5,
            stat_points INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            gloves TEXT DEFAULT 'Потрёпанные перчатки'
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id: int) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def create_user(user_id: int, username: str, path_choice: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if path_choice == "legal":
        title = "Новичок"
        gloves = "Потрёпанные перчатки"
    else:
        title = "Уличный новичок"
        gloves = "Отсутствуют"

    cursor.execute("""
        INSERT OR REPLACE INTO users (
            user_id, username, path, level, exp, health, max_health, stamina, max_stamina,
            dollars, coins, diamonds, title, reborns, strength, speed, endurance, defense,
            reaction, accuracy, crit, stat_points, is_banned, gloves
        ) VALUES (?, ?, ?, 1, 0, 100, 100, 100, 100, 500.0, 0, 0, ?, 0, 10, 10, 10, 10, 10, 10, 5, 0, 0, ?)
    """, (user_id, username or "Неизвестный", path_choice, title, gloves))
    conn.commit()
    conn.close()

def update_user_stat(user_id: int, field: str, value: Any):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

# =====================================================================
# GAME DATA: 20 STARTING NPCS
# =====================================================================
NPCS = [
    {"id": 1, "name": "Артём «Малыш» Волков", "level": 1, "hp": 100, "str": 8, "def": 5, "reward": 100, "exp": 50},
    {"id": 2, "name": "Тимур «Быстрый» Садыков", "level": 3, "hp": 130, "str": 12, "def": 8, "reward": 180, "exp": 90},
    {"id": 3, "name": "Денис «Кулак» Морозов", "level": 5, "hp": 170, "str": 18, "def": 12, "reward": 280, "exp": 150},
    {"id": 4, "name": "Илья «Таран» Ковалёв", "level": 7, "hp": 220, "str": 25, "def": 18, "reward": 400, "exp": 220},
    {"id": 5, "name": "Рустам «Зверь» Алиев", "level": 10, "hp": 300, "str": 35, "def": 25, "reward": 600, "exp": 350},
    {"id": 6, "name": "Марк «Тень» Риверс", "level": 15, "hp": 420, "str": 50, "def": 35, "reward": 900, "exp": 500},
    {"id": 7, "name": "Дамир «Кобра» Алимов", "level": 20, "hp": 580, "str": 70, "def": 50, "reward": 1300, "exp": 750},
    {"id": 8, "name": "Виктор «Мясник» Орлов", "level": 25, "hp": 750, "str": 95, "def": 65, "reward": 1800, "exp": 1000},
    {"id": 9, "name": "Алекс «Гром» Миллер", "level": 30, "hp": 950, "str": 125, "def": 85, "reward": 2500, "exp": 1400},
    {"id": 10, "name": "Рикардо «Разрушитель» Круз", "level": 35, "hp": 1200, "str": 160, "def": 110, "reward": 3500, "exp": 2000},
    {"id": 11, "name": "Максим «Хищник» Волков", "level": 45, "hp": 1600, "str": 210, "def": 150, "reward": 5000, "exp": 3000},
    {"id": 12, "name": "Джейсон «Демон» Брукс", "level": 50, "hp": 2100, "str": 280, "def": 200, "reward": 7500, "exp": 4500},
    {"id": 13, "name": "Александр «Король» Громов", "level": 60, "hp": 2700, "str": 360, "def": 260, "reward": 11000, "exp": 6500},
    {"id": 14, "name": "Мухаммед «Фантом» Рахимов", "level": 70, "hp": 3500, "str": 460, "def": 340, "reward": 16000, "exp": 9500},
    {"id": 15, "name": "Леон «Император» Кинг", "level": 85, "hp": 4500, "str": 600, "def": 440, "reward": 23000, "exp": 14000},
    {"id": 16, "name": "Артур «Бессмертный» Кейн", "level": 100, "hp": 6000, "str": 800, "def": 580, "reward": 35000, "exp": 20000},
    {"id": 17, "name": "Роман «Палач» Ветров", "level": 120, "hp": 8000, "str": 1050, "def": 750, "reward": 50000, "exp": 30000},
    {"id": 18, "name": "Виктор «Абсолют» Дрейк", "level": 150, "hp": 11000, "str": 1400, "def": 1000, "reward": 75000, "exp": 45000},
    {"id": 19, "name": "Даниэль «Бог ринга» Стоун", "level": 180, "hp": 15000, "str": 1900, "def": 1350, "reward": 110000, "exp": 65000},
    {"id": 20, "name": "Алексей «Легенда» Морозов", "level": 200, "hp": 20000, "str": 2500, "def": 1800, "reward": 180000, "exp": 100000}
]

ATTACKS = ["Джеб", "Кросс", "Левый хук", "Правый хук", "Апперкот", "Удар по корпусу", "Двойной джеб"]
DEFENSES = ["Высокий блок", "Низкий блок", "Уклон влево", "Уклон вправо", "Отход назад", "Контратака"]

# =====================================================================
# STATES FOR COMBAT & REGISTRATION
# =====================================================================
class FightState(StatesGroup):
    choosing_attack = State()
    choosing_defense = State()

# =====================================================================
# KEYBOARD BUILDERS
# =====================================================================
def get_main_keyboard():
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="профиль"), KeyboardButton(text="бой")],
            [KeyboardButton(text="нпс"), KeyboardButton(text="характеристики")],
            [KeyboardButton(text="тренировка"), KeyboardButton(text="магазин")],
            [KeyboardButton(text="инвентарь"), KeyboardButton(text="задания")],
            [KeyboardButton(text="перерождение"), KeyboardButton(text="помощь")]
        ],
        resize_keyboard=True
    )
    return markup

def get_combos_inline_keyboard(action_type: str, selected: List[str]):
    actions = ATTACKS if action_type == "attack" else DEFENSES
    buttons = []
    for act in actions:
        buttons.append([InlineKeyboardButton(text=f"➕ {act}", callback_data=f"act_{action_type}_{act}")])
    
    confirm_text = f"✅ Готово ({len(selected)}/4)"
    buttons.append([InlineKeyboardButton(text=confirm_text, callback_data=f"confirm_{action_type}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# =====================================================================
# AIOGRAM HANDLERS
# =====================================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Registration Handler
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = get_user(message.from_user.id)
    if user:
        await message.answer(f"🥊 С возвращением в ринг, {user['username']}!", reply_markup=get_main_keyboard())
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥊 ЛЕГАЛЬНЫЙ БОКС", callback_data="path_legal")],
        [InlineKeyboardButton(text="🩸 БОКC БЕЗ ПРАВИЛ", callback_data="path_street")]
    ])
    await message.answer(
        "🥊 **BOXING LIFE — Добро пожаловать!**\n\n"
        "Выберите ваш стартовый путь развития:\n\n"
        "🥊 **ЛЕГАЛЬНЫЙ БОКС:** Официальные турниры, титулы, спортивная карьера.\n"
        "🩸 **БОКС БЕЗ ПРАВИЛ:** Подпольные бои, уличные бои, нелегальный заработок.",
        reply_markup=kb, parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("path_"))
async def process_path_choice(callback: CallbackQuery):
    path_choice = "legal" if callback.data == "path_legal" else "street"
    create_user(callback.from_user.id, callback.from_user.full_name, path_choice)
    await callback.message.delete()
    path_title = "Легальный бокс" if path_choice == "legal" else "Бокс без правил"
    await callback.message.answer(
        f"✅ Поздравляем! Вы выбрали путь: **{path_title}**.\n"
        f"Ваш путь начат! Используйте меню ниже для тренировок и боёв.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# Profile Handler
@dp.message(F.text.lower() == "профиль")
async def show_profile(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Вы ещё не зарегистрированы! Напишите /start")
        return

    profile_text = (
        f"🥊 **BOXING LIFE — ПРОФИЛЬ**\n\n"
        f"👤 **Боец:** {user['username']}\n"
        f"🏆 **Титул:** {user['title']}\n"
        f"⭐ **Уровень:** {user['level']} (Опыт: {user['exp']})\n"
        f"❤️ **Здоровье:** {user['health']}/{user['max_health']}\n"
        f"⚡ **Выносливость:** {user['stamina']}/{user['max_stamina']}\n\n"
        f"💰 **Баланс:** {user['dollars']:.2f}$\n"
        f"🥊 **Экипировка:** {user['gloves']}\n"
        f"🔄 **Перерождений:** {user['reborns']}"
    )
    await message.answer(profile_text, parse_mode="Markdown")

# NPC Catalog
@dp.message(F.text.lower() == "нпс")
async def show_npcs(message: Message):
    text = "🥊 **СПИСОК ПРОТИВНИКОВ (NPC):**\n\n"
    for npc in NPCS[:10]:
        text += f"**{npc['id']}. {npc['name']}** — Уровень {npc['level']} (HP: {npc['hp']})\n"
    text += "\nДля боя с NPC введите: `бой N` (например: `бой 1`)"
    await message.answer(text, parse_mode="Markdown")

# Combat Flow Initiator
@dp.message(F.text.lower().startswith("бой"))
async def start_fight_command(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Для боя с NPC напишите: `бой <номер>` (Например: `бой 1`)", parse_mode="Markdown")
        return

    try:
        npc_id = int(parts[1])
    except ValueError:
        await message.answer("Укажите правильный номер NPC.")
        return

    npc = next((n for n in NPCS if n["id"] == npc_id), None)
    if not npc:
        await message.answer("NPC с таким номером не найден.")
        return

    await state.update_data(
        npc=npc,
        user_hp=user["health"],
        npc_hp=npc["hp"],
        user_attacks=[],
        user_defenses=[]
    )

    await state.set_state(FightState.choosing_attack)
    kb = get_combos_inline_keyboard("attack", [])
    await message.answer(
        f"🥊 **Бой против {npc['name']} начался!**\n\n"
        f"Ваше HP: {user['health']} | HP Врага: {npc['hp']}\n\n"
        f"Выбери 4 удара для комбинации атаки:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("act_attack_"))
async def select_attack_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("user_attacks", [])
    if len(selected) >= 4:
        await callback.answer("Уже выбрано 4 удара! Нажмите ✅ Готово", show_alert=True)
        return
    act = callback.data.replace("act_attack_", "")
    selected.append(act)
    await state.update_data(user_attacks=selected)
    kb = get_combos_inline_keyboard("attack", selected)
    await callback.message.edit_text(
        f"Выбрано ударов ({len(selected)}/4):\n" + "\n".join([f"• {a}" for a in selected]),
        reply_markup=kb
    )

@dp.callback_query(F.data == "confirm_attack")
async def confirm_attacks(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("user_attacks", [])
    if len(selected) != 4:
        await callback.answer("Необходимо выбрать ровно 4 удара!", show_alert=True)
        return

    await state.set_state(FightState.choosing_defense)
    kb = get_combos_inline_keyboard("defense", [])
    await callback.message.edit_text(
        "🛡 Теперь выберите 4 защитных действия:",
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("act_defense_"))
async def select_defense_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("user_defenses", [])
    if len(selected) >= 4:
        await callback.answer("Уже выбрано 4 защитных действия!", show_alert=True)
        return
    act = callback.data.replace("act_defense_", "")
    selected.append(act)
    await state.update_data(user_defenses=selected)
    kb = get_combos_inline_keyboard("defense", selected)
    await callback.message.edit_text(
        f"Выбрано защитных действий ({len(selected)}/4):\n" + "\n".join([f"• {a}" for a in selected]),
        reply_markup=kb
    )

@dp.callback_query(F.data == "confirm_defense")
async def resolve_fight_round(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = get_user(callback.from_user.id)
    npc = data["npc"]
    
    # Calculate player damage to NPC
    player_damage = 0
    combat_log = ["🥊 **РЕЗУЛЬТАТЫ РАУНДА:**\n"]
    for atk in data["user_attacks"]:
        if random.randint(1, 100) > 85:  # 15% miss
            combat_log.append(f"❌ Ваш [{atk}] промазал!")
        else:
            dmg = user["strength"] * 1.2 + random.randint(2, 8)
            player_damage += dmg
            combat_log.append(f"💥 Ваш [{atk}] нанес {dmg:.1f} урона!")

    # Calculate NPC damage to player
    npc_damage = 0
    for _ in range(4):
        if random.randint(1, 100) <= 20:  # Dodge/Block chance
            combat_log.append(f"🛡 Вы заблокировали/уклонились от атаки NPC!")
        else:
            dmg = max(1, npc["str"] - (user["defense"] * 0.3) + random.randint(1, 5))
            npc_damage += dmg
            combat_log.append(f"🩸 {npc['name']} нанес вам {dmg:.1f} урона!")

    new_user_hp = max(0, data["user_hp"] - npc_damage)
    new_npc_hp = max(0, data["npc_hp"] - player_damage)

    await state.clear()

    if new_npc_hp <= 0:
        reward = npc["reward"]
        exp = npc["exp"]
        update_user_stat(callback.from_user.id, "dollars", user["dollars"] + reward)
        update_user_stat(callback.from_user.id, "exp", user["exp"] + exp)
        combat_log.append(f"\n🎉 **ПОБЕДА!** Вы отправили {npc['name']} в нокаут!")
        combat_log.append(f"💰 Награда: +{reward}$ | ⭐ Опыт: +{exp}")
    elif new_user_hp <= 0:
        combat_log.append(f"\n💔 **ПОРАЖЕНИЕ!** {npc['name']} отправил вас в нокаут.")
    else:
        combat_log.append(f"\n⏳ Раунд завершен. Ваше HP: {new_user_hp:.1f} | HP Врага: {new_npc_hp:.1f}")

    await callback.message.edit_text("\n".join(combat_log), parse_mode="Markdown")

# Characteristics
@dp.message(F.text.lower() == "характеристики")
async def show_stats(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        return
    text = (
        f"📊 **ХАРАКТЕРИСТИКИ ПЕРСОНАЖА:**\n\n"
        f"💪 **Сила:** {user['strength']}\n"
        f"⚡ **Скорость:** {user['speed']}\n"
        f"❤️ **Выносливость:** {user['endurance']}\n"
        f"🛡 **Защита:** {user['defense']}\n"
        f"🧠 **Реакция:** {user['reaction']}\n"
        f"🎯 **Точность:** {user['accuracy']}\n"
        f"🔥 **Крит:** {user['crit']}%\n\n"
        f"✨ **Свободные очки:** {user['stat_points']}"
    )
    await message.answer(text, parse_mode="Markdown")

# Admin Panel (Protected by Telegram ID)
@dp.message(F.text.lower() == "админ панель")
async def admin_panel(message: Message):
    if message.from_user.id != CREATOR_ID:
        await message.answer("❌ Доступ запрещен. Вы не являетесь администратором.")
        return

    text = (
        "⚙️ **АДМИНИСТРАТИВНАЯ ПАНЕЛЬ:**\n\n"
        "• `выдать деньги ID сумма`\n"
        "• `выдать опыт ID сумма`\n"
        "• `выдать уровень ID уровень`\n"
        "• `бан ID причина`\n"
        "• `разбан ID`\n"
        "• `статистика`"
    )
    await message.answer(text, parse_mode="Markdown")

# Help Handler
@dp.message(F.text.lower() == "помощь")
async def show_help(message: Message):
    help_text = (
        "🥊 **КОМАНДЫ BOXING LIFE (пишутся БЕЗ /):**\n\n"
        "• `профиль` — Профиль игрока\n"
        "• `бой <номер>` — Сразиться с NPC\n"
        "• `нпс` — Список противников\n"
        "• `характеристики` — Прокачка и параметры\n"
        "• `тренировка` — Тренировки для роста\n"
        "• `магазин` — Магазин перчаток и экипировки\n"
        "• `инвентарь` — Ваши предметы\n"
        "• `перерождение` — Система перерождений"
    )
    await message.answer(help_text, parse_mode="Markdown")

# =====================================================================
# MAIN ENTRY POINT
# =====================================================================
async def main():
    init_db()
    print("🥊 Бот BOXING LIFE успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())