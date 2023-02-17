class NotSending(Exception):
    """Не отправлять в Телеграм."""

    pass


class TelegramError(NotSending):
    """Ошибка телеграма."""

    pass


class InvalidResponseCode(Exception):
    """Неверный код ответа."""

    pass


class ConnectionError(Exception):
    """Неверный код ответа."""

    pass


class EmptyResponseFromAPI(NotSending):
    """Пустой ответ от API."""

    pass
