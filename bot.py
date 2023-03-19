import aiopg
from aiogram import Bot, Dispatcher, executor, types

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
    tag_raiting_pair = message.text.split()[-2:]
    await message.answer(str(tag_raiting_pair))


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
