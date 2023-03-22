class NotForSend(Exception):
    """Не для пересылки в телеграмм."""
    pass


class TelegramError(NotForSend):
    """Ошибка телеграмма."""
    pass


class BadCodeStatus(Exception):
    """Статус-код ответа не равен 200."""
    pass


class ConnectionToDbFailed(Exception):
    """Не удалось подключиться к базе данных."""
    pass


class ResponseFromApiWasntRecieved(Exception):
    """Не удалось получить ответ от API."""
    pass


class GettingDataFromDbFailed(Exception):
    """Не удалось получить данные из базы."""
    pass


class SendRequestToDbFailed(Exception):
    """Не удалось отправить запрос к базе."""
    pass


class ErrorInCycle(Exception):
    """Ошибка внутри цикла."""
    pass


class UnknownTableName(Exception):
    """Неизвестная таблица."""
    pass

