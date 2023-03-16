import logging
import os
import sys
import time

import psycopg2
import requests
import telegram
from dotenv import load_dotenv

import custom_exceptions

ENDPOINT: str = 'https://codeforces.com/api/problemset.problems?lang=ru'
RETRY_TIME: int = 3600
connection = None

load_dotenv()
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
HOST: str = os.getenv('HOST')
USER: str = os.getenv('USER')
DB_NAME: str = os.getenv('PASSWORD')
PASSWORD: str = os.getenv('DB_NAME')


def connect_to_db():
    logging.info('-------------------Запуск программы-------------------------')
    logging.info('Попытка соединения с PostgreSQL')

    try:
        connect = psycopg2.connect(
            host=HOST, user=USER, password=PASSWORD, database=DB_NAME,
        )
    except Exception as _error:
        raise custom_exceptions.ConnectionToDbFailed(_error)

    logging.info('Соединение с PostgreSQL установлено')
    return connect


def get_data_from_db(request: str) -> tuple:
    try:
        with connection.cursor() as cursor:
            cursor.execute(request)
            return cursor.fetchone()
    except Exception as _error:
        raise custom_exceptions.GettingDataFromDbFailed(_error)


def send_request_to_db(request: str) -> None:
    try:
        with connection.cursor() as cursor:
            cursor.execute(request)
    except Exception as _error:
        raise custom_exceptions.SendRequestToDbFailed(_error)


def send_requests_to_db(request: str, tasks: list) -> None:
    try:
        with connection.cursor() as cursor:
            for i in tasks[::-1]:
                cursor.execute(request, i)
    except Exception as _error:
        raise custom_exceptions.SendRequestToDbFailed(_error)


def check_or_create_table() -> None:
    logging.info("Проверка БД на наличие таблицы tasks")
    response: tuple = get_data_from_db(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_name = 'tasks';
        """
    )
    if not response:
        logging.info("Таблица tasks не найдена, создание новой таблицы")
        send_request_to_db(
            """
            CREATE TABLE tasks(
            id SERIAL PRIMARY KEY,
            tags varchar(255)[] NOT NULL,
            count_solved int NOT NULL,
            name_and_number varchar(255)[2] NOT NULL,
            rating int);
            """
        )
        connection.commit()
        logging.info('Таблица успешно создана, первичное заполнение задачами')
        filling_table(get_parse_response(get_json_response().get('result')))
    else:
        logging.info('Таблица tasks найдена')


def get_json_response() -> dict:
    logging.info("Запрос к API Codeforces и преобразование в формат json")
    try:
        json_response: dict = requests.get(ENDPOINT).json()
    except Exception as _error:
        raise custom_exceptions.ResponseFromApiWasntRecieved(_error)

    if json_response.get('status') != 'OK':
        message: str = 'Сервер с задачами не доступен'
        logging.info(message)
        raise custom_exceptions.BadCodeStatus(message)

    logging.info('Успешно')
    return json_response


def get_parse_response(response: dict) -> list:
    logging.info('Попытка распарсить полученный ответ')
    problems: dict = response.get('problems')
    problems_statistic: dict = response.get('problemStatistics')
    parsed_data: list = []

    for i in range(len(problems)):
        parsed_data.append(
            [
                problems[i].get('tags'),
                problems_statistic[i].get('solvedCount'),
                [
                    problems[i].get('name'),
                    str(problems[i].get('contestId')) + problems[i].get('index')
                ],
                problems[i].get('rating', 0),
            ]
        )

    logging.info('Парсинг прошёл успешно, возврат массива с задачами')
    return parsed_data


def adding_tasks_in_table(
        last_table_record_name: str, parsed_tasks: list) -> None:

    logging.info('Создание и заполнение массива новыми задачами')
    new_tasks: list = []

    for task in parsed_tasks:
        if task[2] != last_table_record_name:
            new_tasks.append(task)
        else:
            break

    logging.info(
        'Массив готов, добавление {} задач в таблицу'.format(len(new_tasks))
    )
    filling_table(new_tasks)


def filling_table(tasks: list) -> None:
    logging.info('Попытка внесения данных в таблицу')
    send_requests_to_db(
        """
        INSERT INTO tasks (tags, count_solved, name_and_number, rating)
        VALUES (%s, %s, %s, %s);
        """, tasks)
    connection.commit()
    logging.info('Данные успешно внесены и сохранены')


def get_last_record_from_table() -> str:
    logging.info('Получение последней записи из таблицы')
    return get_data_from_db(
        """
        SELECT name_and_number FROM tasks
        ORDER BY id DESC LIMIT 1;
        """
    )[0]


def get_count_of_tasks_in_table() -> int:
    logging.info('Получение количества записей в таблице')
    return int(get_data_from_db('SELECT count(*) FROM tasks')[0])


def send_message_to_tg(from_bot: telegram.Bot, message: str) -> None:
    try:
        logging.info("Попытка отправить сообщение")
        from_bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as _error:
        raise custom_exceptions.TelegramError(
            f"Сообщение не отправлено, ошибка - {_error}"
        )
    else:
        logging.info("Сообщение успешно отправлено")


def check_tokens() -> bool:
    logging.info('Проверка наличия всех токенов в файле .env')
    return all(
        [HOST, USER, PASSWORD, DB_NAME, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    )


def main() -> None:
    try:
        if not check_tokens():
            message: str = "Отсутствуют один или несколько токенов!"
            logging.critical(message)
            sys.exit(message)

        logging.info('Токены обнаружены, запуск бота для отправки крит. ошибок')
        try:
            bot: telegram.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
        except Exception as _error:
            raise custom_exceptions.BotStartFailed(_error)
        message = 'Бот запущен'
        logging.info(message)
        send_message_to_tg(bot, message)

        global connection
        connection = connect_to_db()
        check_or_create_table()
        tasks_in_db_count: int = get_count_of_tasks_in_table()
        logging.info('Записей в таблице - {}'.format(tasks_in_db_count))

        while True:
            try:
                logging.info('------------Вход в цикл-------------------------')
                json_response: dict = get_json_response().get('result')
                tasks_response_count: int = len(json_response.get('problems'))
                logging.info('Сравнение количества записей в БД и в ответе')

                if tasks_response_count != tasks_in_db_count:
                    logging.info(
                        """Количество записей в БД и в ответе не равно ({}!={}), 
                        начинаем парсить ответ""".format(
                            tasks_in_db_count, tasks_response_count
                        )
                    )
                    adding_tasks_in_table(
                        get_last_record_from_table(),
                        get_parse_response(json_response)
                    )
                    tasks_in_db_count = tasks_response_count

                else:
                    logging.info(
                        'Количество записей в бд и ответе равно {}=={}'.format(
                            tasks_in_db_count, tasks_response_count
                        )
                    )

            except Exception as _error:
                raise custom_exceptions.ErrorInCycle(_error)

            else:
                logging.info('Ожидание - 1 час')
                time.sleep(RETRY_TIME)

    except custom_exceptions.NotForSend as _error:
        message = f'Бот упал с ошибкой:\n {_error}\n'
        logging.error(message, exc_info=True)

    except Exception as _exception:
        connection.rollback()
        message = f'Ошибка во время работы с PostgreSQL:\n {_exception}\n'
        logging.critical(message, exc_info=True)
        send_message_to_tg(bot, message)

    finally:
        if connection:
            connection.close()
            logging.info('Завершение работы. Соединение с PostgreSQL закрыто')


if __name__ == '__main__':

    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s, %(levelname)s, Путь - %(pathname)s, '
            'Файл - %(filename)s, Функция - %(funcName)s, '
            'Номер строки - %(lineno)d, %(message)s.'
        ),
        handlers=[
            logging.FileHandler('log.txt', encoding='UTF-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()
