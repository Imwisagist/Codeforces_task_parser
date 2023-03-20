import re

import aiopg
import requests
from aiogram import Bot, Dispatcher, executor, types
from bs4 import BeautifulSoup
from requests import Response

import config as cfg

dp = Dispatcher(Bot(token=cfg.TELEGRAM_TOKEN))


class Chapter:
    def __init__(self, task: BeautifulSoup, class_: str, section: str) -> None:
        self.output = self.value = self.title = None
        self.task = task
        self.class_ = class_
        self.activate_fields(section)

    def activate_fields(self, section) -> None:
        if section == 'header':
            self.activate_header_fields()
        elif section == 'i/o':
            self.activate_input_or_output_fields()
        elif section == 'tests':
            self.activate_tests_fields()

    def activate_tests_fields(self) -> None:
        def parsed_data(data):
            input_ = data.find('div', {'class': 'title'})
            value_ = str(
                input_.next_sibling).replace('<br/>', '\n')[5:-6].rstrip()
            input_ = input_.text.strip()
            return f"\n" + input_ + f"\n{cfg.SEP}\n" + value_ + f"\n{cfg.SEP}"

        examples = self.task.find(
            'div', {'class': 'section-title'}).text.strip()

        inputs = self.task.findAll('div', {'class': 'input'})
        outputs = self.task.findAll('div', {'class': 'output'})

        self.output = (examples + f'\n{cfg.SEP}' + parsed_data(inputs[0]) +
                       parsed_data(outputs[0]) + parsed_data(inputs[1]) +
                       parsed_data(outputs[0])
                       )

    def activate_input_or_output_fields(self) -> None:
        self.title = self.task.find('div', {'class': f'{self.class_}'})
        self.value = self.title.next_sibling.text.strip()
        self.title = self.title.text.strip()
        self.output = self.title + f"\n{cfg.SEP}\n" + self.value

    def activate_header_fields(self) -> None:
        self.class_ = self.task.find('div', {'class': f'{self.class_}'})
        self.title = self.class_.find(
            'div', {'class': 'property-title'}).text.strip()
        self.value = str(self.class_.find(
            'div', {'class': 'property-title'}).next_sibling)
        self.output = self.title + ': ' + self.value


async def get_data_from_db(sql_query: str) -> list:
    pool = await aiopg.create_pool(cfg.DSN)

    async with pool.acquire() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(sql_query)
            data = await cursor.fetchall()
        pool.close()

    return data


async def get_unique_tags_or_ratings(column_name: str, tag=None) -> list:
    piece = f"WHERE tag='{tag}'"
    sql_query: str = f"""SELECT DISTINCT {column_name} FROM contests
                {piece if tag else ''} ORDER BY {column_name}"""

    return await parse_db_response(await get_data_from_db(sql_query))


async def parse_db_response(db_response: list) -> list:
    return [str_val[0] for str_val in [tup for tup in db_response]]


async def parse_contest(source_contest: list) -> list:
    parsed_tasks: list = []
    for tuple_tasks in source_contest:
        for tasks_list in tuple_tasks:
            for source_task in tasks_list:
                task = re.sub(cfg.REGEX, "", source_task).split(',')
                idx, *tags, count_solved, name, number_idx, difficulty = task
                parsed_tasks.append(
                    [
                        int(idx), ', '.join(tags),
                        int(count_solved), name, number_idx, int(difficulty)
                    ]
                )
    return parsed_tasks


async def get_task_descriptions(task_url: str) -> str:
    response: Response = requests.get(task_url)
    soup: BeautifulSoup = BeautifulSoup(response.text, 'html.parser')

    header: BeautifulSoup = soup.find('div', {'class': 'header'})
    title: str = header.find('div', {'class': 'title'}).text.strip()
    time_limit: Chapter = Chapter(header, 'time-limit', 'header')
    memory_limit: Chapter = Chapter(header, 'memory-limit', 'header')
    file_input: Chapter = Chapter(header, 'input-file', 'header')
    file_output: Chapter = Chapter(header, 'output-file', 'header')

    task_description: str = soup.find(
        'div', {'class': 'header'}).next_sibling.text.strip()

    input_: BeautifulSoup = soup.find('div', {'class': 'input-specification'})
    input_specification: Chapter = Chapter(input_, 'section-title', 'i/o')

    output_: BeautifulSoup = soup.find('div', {'class': 'output-specification'})
    output_specification: Chapter = Chapter(output_, 'section-title', 'i/o')

    test_soup: BeautifulSoup = soup.find('div', {'class': 'sample-tests'})
    tests: Chapter = Chapter(test_soup, 'input', 'tests')

    result = f"""
{title}\n{'--'*len(title)}
{time_limit.output}
{memory_limit.output}
{cfg.SEP}
{file_input.output}
{file_output.output}
{cfg.SEP}
{task_description}
{cfg.SEP}
{input_specification.output}
{cfg.SEP}
{output_specification.output}
{cfg.SEP}
{tests.output}
"""

    return result


@dp.message_handler(commands=['task'])
async def print_task_description(message: types.Message):
    task_id = int(message.text.split()[-1])
    name_number_index = await get_data_from_db(
        f"SELECT name_and_number FROM tasks WHERE id={task_id}"
    )

    num, idx = name_number_index[-1][-1][-1].split('/')
    await message.answer(
        await get_task_descriptions(
            f"https://codeforces.com/problemset/problem/{num}/{idx}?locale=ru")
    )


@dp.message_handler(commands=['tags'])
async def print_tags(message: types.Message):
    await message.answer(', '.join(await get_unique_tags_or_ratings('tag')))


@dp.message_handler(commands=['ratings'])
async def print_ratings_for_tag(message: types.Message):
    tag = message.text.split()[-1]

    if tag not in await get_unique_tags_or_ratings('tag'):
        return await message.answer('Неизвестная тема')

    source: list = await get_data_from_db(
        f"SELECT DISTINCT rating FROM contests WHERE tag='{tag}'"
    )
    await message.answer(', '.join(map(str, await parse_db_response(source))))


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


@dp.message_handler(commands=['contests'])
async def print_contests_for_tag_and_rating(message: types.Message):
    tag, rating = message.text.split()[-2:]

    tags: list = await get_unique_tags_or_ratings('tag')
    ratings: list = await get_unique_tags_or_ratings('rating', tag)
    if (tag not in tags) or (int(rating) not in ratings):
        return await message.answer('Неизвестная пара тема/сложность')

    response: list = await get_data_from_db(
        f"""
        SELECT id, number, tag, rating from contests 
        WHERE tag='{tag}' and rating='{rating}'
        """
    )
    for contest in response[::-1]:
        await message.answer("""
Идентификатор - {},
Номер контеста - {},
Тема - {},
Сложность - {}""".format(*contest))


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
