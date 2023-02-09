import os
import requests
import time
import sys

import logging
import telegram
from dotenv import load_dotenv

load_dotenv()


logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = 5970585663

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens(tokens):
    """Проверяет доступность переменных окружения."""
    return all(tokens)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'В чат направлено сообщение {message}')
    except Exception as error:
        logging.error(f'Сбой при отправке сообщения {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передается временная метка. В случае
    успешного запроса должна вернуть ответ API, приведя его из формата JSON
    к типам данных Python.
    """
    try:
        payload = {'from_date': timestamp}
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=payload)
        if response.status_code != 200:
            raise Exception('Сервер пал смертью храбрых')
        return response.json()
    except Exception as error:
        logging.error(f'Обшибка при обращении к API. {error}')
        raise Exception(f'Обшибка при обращении к API. {error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации.
    В качестве параметра функция получает ответ API, приведенный к типам
    данных Python.
    """
    if type(response) != dict:
        logging.error('Неверный тип полученных данных (не словарь)')
        raise TypeError
    if 'homeworks' not in response:
        logging.error('В ответе отсутствует ключ homeworks')
        raise KeyError
    if type(response['homeworks']) != list:
        logging.error('Неверный тип полученных данных (не список)')
        raise TypeError
    return response


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент из
    списка домашних работ. В случае успеха, функция возвращает подготовленную
    для отправки в Telegram строку, содержащую один из вердиктов словаря
    HOMEWORK_VERDICTS.
    """
    try:
        if 'homework_name' not in homework:
            raise Exception('В ответе API нет нет ключа homework_name')
        homework_name = homework.get('homework_name')
        status = homework.get('status')
        if status not in HOMEWORK_VERDICTS:
            raise Exception('Такой статус ДЗ мне не знаком.')
        verdict = HOMEWORK_VERDICTS.get(status)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        logging.error(f'Ошибка при определении статуса ДЗ. {error}')
        raise Exception(f'Ошибка при определении статуса ДЗ. {error}')


def main():
    """Основная логика работы бота."""
    logging.info('Старт бота')
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if check_tokens(tokens) is not True:
        logging.critical('Переменные окружения недоступны')
        sys.exit()

    current_status = ''
    timestamp = int(time.time()) - 2629743
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response.get('homeworks')[0]
            if homework.get('status') != current_status:
                current_status = homework.get('status')
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logging.debug('Новых статусов в ответе нет')
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
