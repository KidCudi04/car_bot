import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from data import CARS
from parser import get_cars
 
import os
TOKEN = os.getenv("TOKEN")
 
bot = Bot(token=TOKEN)
dp = Dispatcher()
 
user_state = {}
wishlist = {}
delete_mode = {}
sent_links = {}  # {user_id: set(ссылок)}
 
SYNONYMS = {
    "bmw": ["bmw", "бмв"],
    "toyota": ["toyota", "тойота"],
    "mercedes": ["mercedes", "мерседес", "мерс", "mercedes-benz"],
    "audi": ["audi", "ауди"],
    "lexus": ["lexus", "лексус"],
    "kia": ["kia", "киа"],
    "hyundai": ["hyundai", "хендай"],
    "subaru": ["subaru", "субару"],
    "mazda": ["mazda", "мазда"],
    "ford": ["ford", "форд"],
    "dodge": ["dodge", "додж"],
}
 
 
def normalize(text):
    return text.lower().replace("-", " ").strip()
 
 
def matches(car, wish):
    title = normalize(car["title"])
    car_year = car.get("year", "").strip()
 
    brand = wish["brand"].lower()
    model = wish["model"].lower()
    year = wish.get("year", "")  # пустая строка = год не указан
 
    brand_variants = SYNONYMS.get(brand, [brand])
 
    # Проверяем бренд в названии
    brand_match = any(b in title for b in brand_variants)
 
    # Проверяем модель — берём первое слово модели (например "x7" из "X7")
    model_match = model.split()[0] in title
 
    year_match = True if year == "" else (car_year == year)

    # 🔍 ДЕБАГ
    if brand_match or model_match:
        print(f"title='{title}' | brand={brand_match} | model={model_match} | year={year_match} | wish={brand} {model}")

    return brand_match and model_match and year_match
 
 
def make_keyboard(items):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=item)] for item in items],
        resize_keyboard=True,
    )
 
 
def main_menu():
    return make_keyboard([
        "🚗 Выбрать машину",
        "📌 Мой вишлист",
    ])
 
 
async def process_cars(notify_user_id=None):
    """
    Парсит объявления и рассылает уведомления.
    notify_user_id — если передан, обрабатываем только этого пользователя.
    """
    cars = get_cars(pages=5)
 
    targets = (
        {notify_user_id: wishlist[notify_user_id]}
        if notify_user_id and notify_user_id in wishlist
        else wishlist
    )
 
    for user_id, wishes in targets.items():
        if not wishes:
            continue
 
        is_first = user_id not in sent_links
 
        if is_first:
            sent_links[user_id] = set()
 
        found_any = False
 
        for car in cars:
            matched = False
            for wish in wishes:
                if matches(car, wish):
                    matched = True
                    break
 
            if not matched:
                continue
 
            if car["link"] in sent_links[user_id]:
                continue
 
            sent_links[user_id].add(car["link"])
            found_any = True
 
            header = "📌 Найдено по твоему запросу:" if is_first else "🔥 Новое объявление!"
            year_str = f"\n📅 {car['year']} г." if car.get("year") else ""
 
            text = (
                f"{header}\n\n"
                f"🚗 {car['title']}{year_str}\n"
                f"💰 {car['price']}\n\n"
                f"{car['link']}"
            )
 
            try:
                await bot.send_message(user_id, text)
            except Exception as e:
                print(f"[bot] Ошибка отправки сообщения {user_id}: {e}")
 
        if is_first and not found_any:
            try:
                await bot.send_message(user_id, "😔 По твоему запросу пока ничего не найдено. Уведомлю как появится!")
            except Exception as e:
                print(f"[bot] Ошибка отправки сообщения {user_id}: {e}")
 
 
async def check_cars():
    """Фоновая задача: парсит каждые 60 секунд."""
    while True:
        try:
            print("[bot] Фоновая проверка объявлений...")
            await process_cars()
        except Exception as e:
            print(f"[bot] Ошибка при проверке: {e}")
 
        await asyncio.sleep(60)
 
 
@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()
 
    if user_id not in user_state:
        user_state[user_id] = {}
 
    # ── /start ──────────────────────────────────────────────────────────────
    if text == "/start":
        user_state[user_id] = {}
        delete_mode[user_id] = False
        await message.answer("Главное меню:", reply_markup=main_menu())
 
    # ── Выбрать машину ──────────────────────────────────────────────────────
    elif text == "🚗 Выбрать машину":
        user_state[user_id] = {}
        delete_mode[user_id] = False
        await message.answer("Выбери марку:", reply_markup=make_keyboard(CARS.keys()))
 
    # ── Вишлист ─────────────────────────────────────────────────────────────
    elif text == "📌 Мой вишлист":
        delete_mode[user_id] = False
 
        if not wishlist.get(user_id):
            await message.answer("У тебя пока нет машин 😔", reply_markup=main_menu())
            return
 
        lines = "\n".join(
            f"{i}. 🚗 {car['brand']} {car['model']}"
            + (f" ({car['year']})" if car.get('year') else " (любой год)")
            for i, car in enumerate(wishlist[user_id], start=1)
        )
        await message.answer(
            f"📌 Твой вишлист:\n\n{lines}\n\nНапиши номер, чтобы удалить:"
        )
        delete_mode[user_id] = True
 
    # ── Удаление из вишлиста ────────────────────────────────────────────────
    elif delete_mode.get(user_id):
        delete_mode[user_id] = False
 
        if not text.isdigit():
            await message.answer("Введи число", reply_markup=main_menu())
            return
 
        index = int(text) - 1
        cars_list = wishlist.get(user_id, [])
 
        if 0 <= index < len(cars_list):
            removed = cars_list.pop(index)
            year_str = f" ({removed['year']})" if removed.get('year') else ""
            await message.answer(
                f"❌ Удалено: {removed['brand']} {removed['model']}{year_str}",
                reply_markup=main_menu(),
            )
        else:
            await message.answer("Неверный номер", reply_markup=main_menu())
 
    # ── Выбор марки ─────────────────────────────────────────────────────────
    elif text in CARS:
        user_state[user_id]["brand"] = text
        await message.answer(
            "Выбери модель:",
            reply_markup=make_keyboard(CARS[text]),
        )
 
    # ── Выбор модели ────────────────────────────────────────────────────────
    elif (
        "brand" in user_state[user_id]
        and text in CARS.get(user_state[user_id]["brand"], [])
    ):
        user_state[user_id]["model"] = text
        # 🔥 Предлагаем ввести год или пропустить
        await message.answer(
            "✏️ Введи год (например: 2022) или пропусти:",
            reply_markup=make_keyboard(["⏭ Пропустить год"]),
        )
 
    # ── Ввод года или пропуск ───────────────────────────────────────────────
    elif "brand" in user_state[user_id] and "model" in user_state[user_id]:
 
        if text == "⏭ Пропустить год":
            user_state[user_id]["year"] = ""  # без фильтра по году
        elif not text.isdigit():
            await message.answer("Введи корректный год (например: 2022) или нажми «⏭ Пропустить год»")
            return
        else:
            year = int(text)
            if not (1990 <= year <= 2025):
                await message.answer("Введи год от 1990 до 2025 или нажми «⏭ Пропустить год»")
                return
            user_state[user_id]["year"] = str(year)
 
        data = user_state[user_id].copy()
 
        if user_id not in wishlist:
            wishlist[user_id] = []
 
        wishlist[user_id].append(data)
 
        # 🔥 Сбрасываем историю — бот сразу найдёт все объявления
        sent_links.pop(user_id, None)
 
        year_display = data['year'] if data.get('year') else "любой"
        await message.answer(
            f"✅ Добавлено в вишлист:\n\n"
            f"🚗 {data['brand']} {data['model']}\n"
            f"📅 {year_display}\n\n"
            f"🔍 Ищу объявления...",
            reply_markup=main_menu(),
        )
 
        user_state[user_id] = {}
 
        # 🔥 Мгновенный поиск — не ждём 60 сек
        asyncio.create_task(process_cars(notify_user_id=user_id))
 
    # ── Всё остальное ───────────────────────────────────────────────────────
    else:
        await message.answer("Нажми /start", reply_markup=main_menu())
 
 
async def main():
    asyncio.create_task(check_cars())
    await dp.start_polling(bot)
 
 
if __name__ == "__main__":
    asyncio.run(main())