import logging
import os
import sys
from logging import Logger

from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
USER = DB_NAME = PASSWORD = 'postgres'
HOST: str = 'db'   # localhost для локального запуска db для докера
PORT: int = 5432

# For Windows
# import asyncio
# asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
DSN: str = f'dbname={DB_NAME} user={USER} password={PASSWORD} host={HOST}'
REGEX: str = r"[^a-zA-Zа-яА-Я0-9, ]+"
SEP: str = '--'*25


def get_logger(logger_name: str, logfile_name: str) -> Logger:

    logger: Logger = logging.getLogger(logger_name)

    logger.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_formatter = logging.Formatter(
        "%(name)s %(levelname)s %(funcName)s %(lineno)d %(message)s")
    stream_handler.setFormatter(stream_formatter)
    stream_handler.addFilter(logging.Filter(logger_name))
    logger.addHandler(stream_handler)

    logs_dir_path: str = ''.join((os.getcwd(), '/logs'))
    if not os.path.exists(logs_dir_path):
        os.makedirs(logs_dir_path)

    file_handler = logging.FileHandler(
        f'logs/{logfile_name}.txt', encoding='UTF-8')
    file_formatter = logging.Formatter(
            '%(asctime)s, %(levelname)s, Путь - %(pathname)s, '
            'Файл - %(filename)s, Функция - %(funcName)s, '
            'Номер строки - %(lineno)d, %(message)s.'
        )
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(logging.Filter(logger_name))
    logger.addHandler(file_handler)

    return logger
