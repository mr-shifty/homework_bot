import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TG_CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS: list = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> str:
    """Проверка наличия всех токенов."""
    logging.info('Проверка наличия всех токенов')
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message) -> str:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение "{message}"')
    except telegram.error.TelegramError as error:
        logging.error(f'Бот не отправил сообщение "{message}": {error}')
        raise exceptions.SendMessageError(
            f'Ошибка при отправки сообщения: {error}'
        )
    else:
        logging.info('Сообщение успешно отправлено')


def get_api_answer(timestamp: int):
    """Получить статус домашки."""
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        logging.info(
            'начало запроса:'
            'url = {url},'
            'headers = {headers},'
            'params = {params}'.format(**params_request)
        )
        homeworks_statuses = requests.get(**params_request)
        if homeworks_statuses.status_code != HTTPStatus.OK:
            raise exceptions.InvalidResponseCode(
                'Не удалось получить ответ API'
                f'Ошибка: {homeworks_statuses.status_code}'
                f'Причина: {homeworks_statuses.reason}'
                f'Текст: {homeworks_statuses.text}'
            )
        return homeworks_statuses.json()
    except Exception:
        raise exceptions.ConnectionError(
            'Неверный код ответа'
            'url = {url},'
            'headers = {headers},'
            'params = {params}'.format(**params_request)
        )


def check_response(response) -> list:
    """Проверка валидности ответа."""
    logging.debug('Старт проверки')
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    if 'homeworks' not in response or 'current_date' not in response:
        raise exceptions.EmptyResponseFromAPI('Пустой ответ от API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является списком')
    return homeworks


def parse_status(homework):
    """Извлекает из конкретной домашней работы её статус."""
    if 'homework_name' not in homework:
        raise KeyError('Ключ homework_name отсутствует в homework')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('Ключ status отсутствует в homework')
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Статус {homework_status} неизвестен')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствуют необходимые переменные окружения')
        sys.exit('Выход из программы')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_report = {
        'name': '',
        'output': ''
    }
    preview_report = current_report.copy()
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get(
                'current_date',
                int(time.time())
            )
            new_homeworks = check_response(response)
            if new_homeworks:
                homework = new_homeworks[0]
                current_report['name'] = homework.get('homework_name')
                current_report['output'] = homework.get('status')
            else:
                current_report = 'Нет новых статусов'
            if current_report != preview_report:
                send = f'{current_report["name"], current_report["output"]}'
                send_message(bot, send)
                preview_report = current_report.copy
            send_message(bot, parse_status(new_homeworks[0]))
        except exceptions.NotSending as error:
            message = f'Сбой в работе прораммы {error}'
            logging.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_report['output'] = message
            logging.error(message)
            if current_report != preview_report:
                send_message(bot, message)
                preview_report = current_report.copy
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s, %(levelname)s,'
            '%(pathname)s, %(filename)s,'
            '%(funcName)s, %(lineno)d, %(message)s'
        ),
        handlers=[
            logging.FileHandler('log.txt', encoding='UTF-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    main()
