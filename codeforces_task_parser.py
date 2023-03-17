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
    logging.info('Соединение с PostgreSQL')

    try:
        connect = psycopg2.connect(
            host=HOST, user=USER, password=PASSWORD, database=DB_NAME,
        )
    except Exception as _error:
        raise custom_exceptions.ConnectionToDbFailed(_error)

    return connect


def get_data_from_db(request: str) -> list:
    try:
        with connection.cursor() as cursor:
            cursor.execute(request)
            return cursor.fetchall()
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
    response: list = get_data_from_db(
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

    return json_response


def get_parse_response(response: dict) -> list:
    logging.info('Парсинг полученного ответа')
    problems: dict = response.get('problems')
    problems_statistic: dict = response.get('problemStatistics')
    parsed_data: list = []

    for i in range(len(problems)):
        tags = problems[i].get('tags')
        if not tags:
            tags = ['TaskWithoutTags']
        parsed_data.append(
            [
                tags,
                problems_statistic[i].get('solvedCount'),
                [
                    problems[i].get('name'),
                    str(problems[i].get('contestId')) + problems[i].get('index')
                ],
                problems[i].get('rating', 0),
            ]
        )

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
        f'Добавление {len(new_tasks)} задач в таблицу'
    )
    filling_table(new_tasks)


def filling_table(tasks: list) -> None:
    logging.info('Внесение данных в таблицу')
    send_requests_to_db(
        """
        INSERT INTO tasks (tags, count_solved, name_and_number, rating)
        VALUES (%s, %s, %s, %s);
        """, tasks)
    connection.commit()


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
    return int(*get_data_from_db('SELECT count(*) FROM tasks')[0])


def send_message_to_tg(from_bot: telegram.Bot, message: str) -> None:
    try:
        logging.info("Отправка сообщения")
        from_bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as _error:
        raise custom_exceptions.TelegramError(
            f'Сообщение не отправлено, ошибка - {_error}'
        )


def check_tokens() -> bool:
    logging.info('Проверка наличия всех токенов в файле .env')
    return all(
        [HOST, USER, PASSWORD, DB_NAME, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    )


def get_unique_tags_and_rating() -> tuple:
    logging.info('Запрос тем и рейтингов из базы')
    tags_ratings: list = get_data_from_db('SELECT tags, rating FROM tasks;')

    unique_tags: list = []
    unique_rating: list = []

    logging.info('Подготовка данных, поиск уникальных тем и сложностей задач')
    for tags_tuple in tags_ratings:
        for tag in tags_tuple[0]:
            if tag not in unique_tags:
                unique_tags.append(tag)
        if tags_tuple[1] not in unique_rating:
            unique_rating.append(tags_tuple[1])

    return sorted(unique_tags), sorted(unique_rating)


def get_contests(unique_tags: list, unique_rating: list) -> dict:
    logging.info('Запрос всех задач из базы')
    tasks: list = get_data_from_db(
        """
        SELECT tags, count_solved, name_and_number, rating FROM tasks;
        """
    )

    logging.info(
        'Подсчёт, как часто встречается тема и сортировка по не убыванию'
    )
    tag_meet_frequency: dict = {}
    for utag in unique_tags:
        for task in tasks:
            if utag in task[0]:
                tag_meet_frequency[utag] = tag_meet_frequency.get(utag, 0) + 1
    asc_sorted_tags: dict = {k: v for k, v in sorted(
        tag_meet_frequency.items(), key=lambda item: item[1]
    )}

    contests: dict = {}
    given_tasks_ids: list[str] = ['0']
    contest_num: int = 0
    sorted_unique_tags_copy: list = list(asc_sorted_tags.keys())

    logging.info('Создание контестов')
    while sorted_unique_tags_copy:
        for utag in sorted_unique_tags_copy:
            empty: bool = True
            for urating in unique_rating:
                data: list = get_data_from_db(
                    f"""
                    SELECT * FROM tasks WHERE '{utag}'=ANY(tags) 
                    AND rating={urating} 
                    AND id not in ({', '.join(given_tasks_ids)}) LIMIT 10;
                    """
                )
                if data:
                    empty = False
                    for task in data:
                        given_tasks_ids.append(str(task[0]))
                    contests[str(contest_num)+')'+utag+'/'+str(urating)] = data
            if empty:
                sorted_unique_tags_copy.remove(utag)
        contest_num += 1

    return contests


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
        contests: dict = get_contests(*get_unique_tags_and_rating())

        while True:
            try:
                logging.info('------------Вход в цикл-------------------------')
                json_response: dict = get_json_response().get('result')
                tasks_response_count: int = len(json_response.get('problems'))
                logging.info('Сравнение количества записей в БД и в ответе')

                if tasks_response_count != tasks_in_db_count:
                    logging.info(
                        f"""Количество записей в БД и в ответе не равно 
                        ({tasks_in_db_count}!={tasks_response_count}), 
                        начинаем парсить ответ"""
                        )

                    adding_tasks_in_table(
                        get_last_record_from_table(),
                        get_parse_response(json_response)
                    )
                    contests = get_contests(*get_unique_tags_and_rating())
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
