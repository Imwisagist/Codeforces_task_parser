import sys
import time

import psycopg2
import requests
import telegram

import config as cfg
import custom_exceptions


def connect_to_db():
    log.info('-------------------Запуск программы-------------------------')
    log.info('Соединение с PostgreSQL')

    try:
        connect = psycopg2.connect(
            host=cfg.HOST, user=cfg.USER,
            password=cfg.PASSWORD, database=cfg.DB_NAME,
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


def get_json_response() -> dict:
    log.info("Запрос к API Codeforces и преобразование в формат json")
    try:
        json_response: dict = requests.get(cfg.ENDPOINT).json()
    except Exception as _error:
        raise custom_exceptions.ResponseFromApiWasntRecieved(_error)

    if json_response.get('status') != 'OK':
        message: str = 'Сервер с задачами не доступен'
        log.info(message)
        raise custom_exceptions.BadCodeStatus(message)

    return json_response


def get_parse_response(response: dict) -> list:
    log.info('Парсинг полученного ответа')
    problems: dict = response.get('problems')
    problems_statistic: dict = response.get('problemStatistics')
    parsed_data: list = []

    for i in range(len(problems)):
        tags = problems[i].get('tags')
        if not tags:
            tags = ['task without tags']
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
    log.info('Создание и заполнение массива новыми задачами')
    new_tasks: list = []

    for task in parsed_tasks:
        if task[2] != last_table_record_name:
            new_tasks.append(task)
        else:
            break

    log.info(
        f'Добавление {len(new_tasks)} задач в таблицу'
    )
    filling_table('tasks', new_tasks)
    send_request_to_db('DROP TABLE contests')
    check_or_create_table(('contests', cfg.CONTESTS_MAKE_SQL_QUERY))


def filling_table(table_name: str, content: list) -> None:
    log.info('Внесение данных в таблицу')

    if table_name == 'tasks':
        sql_query = cfg.FILLING_TASKS_TABLE_SQL_QUERY
    elif table_name == 'contests':
        sql_query = cfg.FILLING_CONTESTS_TABLE_SQL_QUERY
    else:
        raise custom_exceptions.UnknownTableName('Неизвестная таблица')

    send_requests_to_db(sql_query, content)
    connection.commit()


def get_last_record_from_table() -> str:
    log.info('Получение последней записи из таблицы')
    return get_data_from_db(
        """
        SELECT name_and_number FROM tasks
        ORDER BY id DESC LIMIT 1;
        """
    )[0]


def get_count_of_records_in_table(table_name: str) -> int:
    log.info(f'Получение количества записей в таблице {table_name}')
    return int(*get_data_from_db(f'SELECT count(*) FROM {table_name}')[0])


def send_message_to_tg(from_bot: telegram.Bot, message: str) -> None:
    try:
        log.info("Отправка сообщения")
        from_bot.send_message(cfg.TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as _error:
        raise custom_exceptions.TelegramError(
            f'Сообщение не отправлено, ошибка - {_error}'
        )


def check_tokens() -> bool:
    log.info('Проверка наличия всех токенов в файле .env')
    return all(
        [
            cfg.HOST, cfg.USER, cfg.PASSWORD,
            cfg.DB_NAME, cfg.TELEGRAM_TOKEN, cfg.TELEGRAM_CHAT_ID
        ]
    )


def get_unique_tags_and_rating() -> tuple:
    log.info('Запрос тем и рейтингов из базы')
    tags_ratings: list = get_data_from_db('SELECT tags, rating FROM tasks;')

    unique_tags: list = []
    unique_rating: list = []

    log.info('Подготовка данных, поиск уникальных тем и сложностей задач')
    for tags_tuple in tags_ratings:
        for tag in tags_tuple[0]:
            if tag not in unique_tags:
                unique_tags.append(tag)
        if tags_tuple[1] not in unique_rating:
            unique_rating.append(tags_tuple[1])

    return sorted(unique_tags), sorted(unique_rating)


def get_contests(unique_tags: list, unique_rating: list) -> list:
    log.info('Запрос всех задач из базы')
    tasks: list = get_data_from_db(
        """
        SELECT tags, count_solved, name_and_number, rating FROM tasks;
        """
    )

    log.info(
        'Подсчёт, как часто встречается тема и сортировка по неубыванию'
    )
    tag_meet_frequency: dict = {}
    for utag in unique_tags:
        for task in tasks:
            if utag in task[0]:
                tag_meet_frequency[utag] = tag_meet_frequency.get(utag, 0) + 1
    asc_sorted_tags: dict = {k: v for k, v in sorted(
        tag_meet_frequency.items(), key=lambda item: item[1]
    )}

    contests: list = []
    given_tasks_ids: list[str] = ['0']
    contest_num: int = 0
    sorted_unique_tags_copy: list = list(asc_sorted_tags.keys())

    log.info('Создание контестов')
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
                    contests.append((contest_num, utag, urating, data))
            if empty:
                sorted_unique_tags_copy.remove(utag)
        contest_num += 1

    return contests


def check_or_create_table(table_name_and_sql_query: tuple) -> None:
    for table_name, sql_query in table_name_and_sql_query:
        log.info(f'Проверка БД на наличие таблицы {table_name}')
        response: list = get_data_from_db(
            f"""
            SELECT table_name FROM information_schema.tables
            WHERE table_name = '{table_name}';
            """
        )
        if not response:
            log.info(f'Таблица {table_name} не найдена, создание новой таблицы')
            send_request_to_db(sql_query)
            connection.commit()
            log.info(f'Таблица {table_name} создана, первичное заполнение')
            if table_name == 'contests':
                content = get_contests(*get_unique_tags_and_rating())
            elif table_name == 'tasks':
                content = get_parse_response(get_json_response().get('result'))
            else:
                raise custom_exceptions.UnknownTableName('Неизвестная таблица')
            filling_table(table_name, content)


def main() -> None:
    try:
        if not check_tokens():
            message: str = "Отсутствуют один или несколько токенов!"
            log.critical(message)
            sys.exit(message)

        log.info('Токены обнаружены, запуск бота для отправки крит. ошибок')
        try:
            bot: telegram.Bot = telegram.Bot(token=cfg.TELEGRAM_TOKEN)
        except Exception as _error:
            raise custom_exceptions.BotStartFailed(_error)
        message = 'Бот запущен'
        log.info(message)
        send_message_to_tg(bot, message)

        global connection
        connection = connect_to_db()
        check_or_create_table(
            (
                ('tasks', cfg.TASKS_MAKE_SQL_QUERY),
                ('contests', cfg.CONTESTS_MAKE_SQL_QUERY),
            ),

        )
        tasks_in_db_count: int = get_count_of_records_in_table('tasks')
        log.info(f'Задач в таблице - {tasks_in_db_count}')
        log.info(
            f'Контестов в таблице - {get_count_of_records_in_table("contests")}'
        )

        while True:
            try:
                log.info('------------Вход в цикл-------------------------')
                json_response: dict = get_json_response().get('result')
                tasks_response_count: int = len(json_response.get('problems'))
                log.info('Сравнение количества записей в БД и в ответе')

                if tasks_response_count != tasks_in_db_count:
                    log.info(
                        f"""Количество записей в БД и в ответе не равно 
                        ({tasks_in_db_count}!={tasks_response_count}), 
                        начинаем парсить ответ"""
                        )
                    adding_tasks_in_table(
                       get_last_record_from_table(),
                       get_parse_response(json_response.get('result'))
                    )
                    tasks_in_db_count = tasks_response_count
                else:
                    log.info(
                        'Количество записей в бд и ответе равно {}=={}'.format(
                            tasks_in_db_count, tasks_response_count
                        )
                    )

            except Exception as _error:
                raise custom_exceptions.ErrorInCycle(_error)

            else:
                log.info('Ожидание - 1 час')
                time.sleep(cfg.RETRY_TIME)

    except custom_exceptions.NotForSend as _error:
        message = f'Бот упал с ошибкой:\n {_error}\n'
        log.error(message, exc_info=True)

    except Exception as _exception:
        connection.rollback()
        message = f'Ошибка во время работы с PostgreSQL:\n {_exception}\n'
        log.critical(message, exc_info=True)
        send_message_to_tg(bot, message)

    finally:
        if connection:
            connection.close()
            log.info('Завершение работы. Соединение с PostgreSQL закрыто')


if __name__ == '__main__':
    log = cfg.get_logger('task_parser', 'task_parser_log')
    main()
