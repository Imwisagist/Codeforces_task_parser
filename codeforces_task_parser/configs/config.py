import asyncio
import logging
import os
import sys
from logging import Logger

from dotenv import load_dotenv

ENDPOINT: str = 'https://codeforces.com/api/problemset.problems?lang=ru'
RETRY_TIME: int = 3600

load_dotenv()
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
USER = DB_NAME = PASSWORD = 'postgres'
HOST: str = 'localhost'   # localhost для локального запуска # db для докера
PORT: int = 5432

DSN: str = f'dbname={DB_NAME} user={USER} password={PASSWORD} host={HOST}'
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

CONTESTS_TABLE_MAKE_SQL_QUERY: str = """
CREATE TABLE contests(id SERIAL PRIMARY KEY, number int NOT NULL,
tag varchar(255) NOT NULL, rating int NOT NULL, tasks varchar(255)[] NOT NULL);
"""
TASKS_TABLE_MAKE_SQL_QUERY: str = """
CREATE TABLE tasks(id SERIAL PRIMARY KEY, tags varchar(255)[] NOT NULL,
count_solved int NOT NULL, name_and_number varchar(255)[2] NOT NULL,rating int);
"""
FILLING_TASKS_TABLE_SQL_QUERY: str = """
INSERT INTO tasks (tags, count_solved, name_and_number, rating)
VALUES (%s, %s, %s, %s);
"""
FILLING_CONTESTS_TABLE_SQL_QUERY: str = """
INSERT INTO contests (number, tag, rating, tasks)
VALUES (%s, %s, %s, %s);
"""


def get_logger(logger_name: str, logfile_name: str) -> Logger:

    logger: Logger = logging.getLogger(logger_name)

    logger.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_formatter = logging.Formatter(
        "%(name)s %(levelname)s %(funcName)s %(lineno)d %(message)s")
    stream_handler.setFormatter(stream_formatter)
    stream_handler.addFilter(logging.Filter(logger_name))
    logger.addHandler(stream_handler)

    logs_dir_path: str = ''.join((os.path.dirname(os.getcwd()), '/logs'))
    if not os.path.exists(logs_dir_path):
        os.makedirs(logs_dir_path)

    file_handler = logging.FileHandler(
        f'{logs_dir_path}/{logfile_name}.txt', encoding='UTF-8')
    file_formatter = logging.Formatter(
            '%(asctime)s, %(levelname)s, Путь - %(pathname)s, '
            'Файл - %(filename)s, Функция - %(funcName)s, '
            'Номер строки - %(lineno)d, %(message)s.'
        )
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(logging.Filter(logger_name))
    logger.addHandler(file_handler)

    return logger
