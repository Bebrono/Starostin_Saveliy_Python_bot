import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
import asyncpg
from parser.parser import *

API_TOKEN = "7736309381:AAFn3bpIivFVG52dfsuJo2wnusz9UquWZ50"  # Вставьте сюда токен вашего бота

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Состояния для сбора команд
collecting_teams = False  # Флаг для отслеживания процесса сбора команд
user_team = []
enemy_team = []


# Подключение к базе данных PostgreSQL
async def get_db_connection():
    return await asyncpg.connect(user='dota_user2', password='1234', database='dota_db', host='dota_db')


# Функция для получения информации о герое по имени
async def get_hero_info(name: str):
    conn = await get_db_connection()
    try:
        query = """
        SELECT name, win_rate, best_aspect, best_aspect_win_rate, best_aspect_pick_rate, strong_against, weak_against
        FROM heroes
        WHERE name ILIKE $1
        """
        hero = await conn.fetchrow(query, name)
        if hero:
            def parse_hero_list(hero_data):
                hero_data = hero_data.strip('{}')
                return [hero.strip('"').strip() for hero in hero_data.split(',')] if hero_data else []

            strong_against = "\n".join(parse_hero_list(hero['strong_against'])) if hero['strong_against'] else "No data"
            weak_against = "\n".join(parse_hero_list(hero['weak_against'])) if hero['weak_against'] else "No data"

            return (
                f"Герой: {hero['name']}\n"
                f"Винрейт: {hero['win_rate']:.2f}%\n"
                f"Бери аспект: {hero['best_aspect'] or 'N/A'}\n"
                f"Винрейт с аспектом: {hero['best_aspect_win_rate']:.2f}%\n"
                f"Пикрейт аспекта: {hero['best_aspect_pick_rate']:.2f}%\n\n"
                f"Силен против:\n{strong_against}\n\n"
                f"Слаб против:\n{weak_against}"
            )
        else:
            return "Герой не найден."
    finally:
        await conn.close()


# Обработчик команды /start
@dp.message(CommandStart())
async def send_welcome(message: Message):
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text='Обо мне!'),
         KeyboardButton(text='АААААААА!'),
         KeyboardButton(text='обновить бд!'),
         KeyboardButton(text='делаем ставки!')]
    ],
        resize_keyboard=True,
        input_field_placeholder='Нажмите чтобы начать',
    )
    await message.answer("Привет, я запустился! Для начала обнови БД! Потом можете ввести имя героя, чтобы узнать его статистику. Нажмите обо мне, чтобы узнать больше.", reply_markup=keyboard)


@dp.message(F.text == "Обо мне!")
async def send_about(message: Message):
    await message.answer("Напиши полное имя героя, и я тебе быстро скажу его винрейт, какой аспект брать, и против кого хорош/плох. Также ты можешь нажать на кнопку (делаем ставки!) чтобы оценить верояность победы твоей команды против вражеской")


@dp.message(F.text == "АААААААА!")
async def send_chlen(message: Message):
    await message.answer("АААААААА?")


@dp.message(F.text == "обновить бд!")
async def update_db(message: Message):
    await message.answer("начато обновление - ожидайте и ничего не нажимайте")
    heroes = scrape_heroes()
    if heroes:
        save_heroes_to_db(heroes)
    await message.answer("БД обновилось!")


@dp.message(F.text == "делаем ставки!")
async def start_betting(message: Message):
    global collecting_teams, user_team, enemy_team
    collecting_teams = True
    user_team = []
    enemy_team = []
    await message.answer("Начнем сбор команды! Введите имя первого героя для вашей команды.")


@dp.message()
async def handle_message(message: Message):
    global collecting_teams, user_team, enemy_team

    hero_name = message.text.strip()

    if collecting_teams:
        if hero_name in user_team or hero_name in enemy_team:
            await message.answer("Этот герой уже добавлен в одну из команд. Выберите другого героя.")
            return

        if len(user_team) < 5:
            # Добавляем героя в команду пользователя
            info = await get_hero_info(hero_name)
            if info != "Герой не найден.":
                user_team.append(hero_name)
                await message.answer(f"Герой {hero_name} добавлен в вашу команду!")
                if len(user_team) == 5:
                    await message.answer("Теперь вводим героев для команды противника.")
            else:
                await message.answer("Герой не найден, попробуйте снова.")
        elif len(enemy_team) < 5:
            # Добавляем героя в команду противника
            info = await get_hero_info(hero_name)
            if info != "Герой не найден.":
                enemy_team.append(hero_name)
                await message.answer(f"Герой {hero_name} добавлен в команду противника!")
                if len(enemy_team) == 5:
                    # Подсчет среднего винрейта
                    user_avg = await calculate_average_win_rate(user_team)
                    enemy_avg = await calculate_average_win_rate(enemy_team)
                    result = f"Средний винрейт вашей команды: {user_avg:.2f}%\n" \
                             f"Средний винрейт команды противника: {enemy_avg:.2f}%\n"
                    result += "Смело даблите!" if user_avg > enemy_avg else "ГГ, проиграли."
                    await message.answer(result)
                    collecting_teams = False
            else:
                await message.answer("Герой не найден, попробуйте снова.")
    else:
        # Поиск информации о герое, если сбор команды не идет
        info = await get_hero_info(hero_name)
        await message.answer(info)


async def calculate_average_win_rate(team):
    total_win_rate = 0
    for hero in team:
        hero_info = await get_hero_info(hero)
        if hero_info != "Герой не найден.":
            total_win_rate += float(hero_info.split("\n")[1].split(": ")[1].strip('%'))
    return total_win_rate / len(team)




# Запуск бота
async def main():
    print("Бот запустился...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()  # Явно создаем цикл событий
    try:
        loop.run_until_complete(main())  # Запускаем основной цикл
    except KeyboardInterrupt:
        print("а все, бот умер брат")
    finally:
        loop.close()
