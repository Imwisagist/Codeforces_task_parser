import aiopg
import requests
from aiogram import Bot, Dispatcher, executor, types
import re
import config as cfg

dp = Dispatcher(Bot(token=cfg.TELEGRAM_TOKEN))


async def get_data_from_db(sql_query: str) -> list:
    pool = await aiopg.create_pool(cfg.DSN)

    async with pool.acquire() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(sql_query)
            response = await cursor.fetchall()

        pool.close()

    return response


async def get_tags() -> list:
    source_tags: list = await get_data_from_db(
        'SELECT DISTINCT tag FROM contests ORDER BY tag'
    )
    return await parse_db_response(source_tags)


async def parse_db_response(response: list) -> list:
    parsed_response: list = []

    for tuple_value in response:
        for str_value in tuple_value:
            parsed_response.append(str_value)

    return parsed_response


@dp.message_handler(commands=['tags'])
async def print_tags(message: types.Message):
    await message.answer(', '.join(await get_tags()))


@dp.message_handler(commands=['ratings'])
async def print_ratings_for_tag(message: types.Message):
    tag = message.text.split()[-1]

    if tag not in await get_tags():
        return await message.answer('Неизвестная тема')

    source: list = await get_data_from_db(
        f"SELECT DISTINCT rating FROM contests WhERE tag='{tag}'"
    )
    await message.answer(', '.join(map(str, await parse_db_response(source))))


@dp.message_handler(commands=['contests'])
async def print_contests_for_tag_and_rating(message: types.Message):
    tag_difficulty: list = message.text.split()[-2:]
    response: list = await get_data_from_db(
        f"""
        SELECT id, number, tag, rating from contests 
        Where tag='{tag_difficulty[0]}' and rating='{int(tag_difficulty[1])}'
        """
    )
    for contest in response[::-1]:
        await message.answer("""
Идентификатор - {},
Номер контеста - {},
Тема - {},
Сложность - {}""".format(*contest))


async def parse_contest(source_contest: list) -> list:
    parsed_tasks: list = []
    regex = r"[^a-zA-Zа-яА-Я0-9, ]+"
    for tasks in source_contest:
        for j in tasks:
            for pi in j:
                pi = re.sub(regex, "", pi)
                pi = pi.split(',')
                id, *tags, count, name, number_idx, difficulty = pi
                parsed_tasks.append(
                    [
                        int(id), ', '.join(tags),
                        int(count), name, number_idx, int(difficulty)
                    ]
                )
    return parsed_tasks


@dp.message_handler(commands=['contest'])
async def print_tasks_from_define_contest(message: types.Message):
    contest_id = int(message.text.split()[-1])
    source_contest = await get_data_from_db(
        f"SELECT tasks from contests Where id={contest_id}"
    )
    [await message.answer("""
Идентификатор - {},
Темы - ({}),
Решено раз - {},
Название - "{}", 
Номер и индекс - {},
Сложность - {},
""".format(*task)) for task in await parse_contest(source_contest)]


@dp.message_handler(commands=['task'])
async def print_task_description(message: types.Message):
    task_id = int(message.text.split()[-1])
    name_number_index = await get_data_from_db(
        f"SELECT name_and_number FROM tasks WHERE id={task_id}"
    )

    number = name_number_index[-1][-1][-1][-2::-1]
    index = name_number_index[-1][-1][-1][-1]
    await message.answer(
        f"https://codeforces.com/problemset/problem/{number}/{index}"
    )


@dp.message_handler(commands=['help'])
async def get_some_help(message: types.Message):
    await message.answer("""
Уточнения:\n
1)"task without tags" среди тем означает что у этой задачи тема не задана.
2)"0" среди рейтингов означает что у этой задачи рейтинг не задан.
""")


@dp.message_handler(commands=['start'])
async def begin_info(message: types.Message):
    await message.answer("""
Список доступных команд:\n
Уточнения некоторых моментов: /help
Получить все доступные темы контестов: /tags
Получить все доступные сложности для темы: /ratings tag
Получить контесты по теме и сложности: /contests tag rating
Получить задачи из контеста: /contest id_contest
Получить описание задачи: /task task_id
""")


@dp.message_handler()
async def unknown_command(message: types.Message):
    log.info('Вход')
    await message.answer(
        'Привет, отправь команду /start чтобы узнать доступные команды'
    )


if __name__ == '__main__':
    log = cfg.get_logger('bot', 'bot_log')
    executor.start_polling(dp, skip_updates=True)
