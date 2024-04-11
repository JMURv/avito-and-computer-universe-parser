import os
from time import sleep
from loguru import logger
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = 'https://www.avito.ru'
MAX_DESCRIPTION_WORDS_LENGTH = 40

PROXIES = os.getenv("PROXIES").split(";")
CURR_PROXY = 0


def parse_info(page: str) -> dict[str, str]:
    info = {
        'link': '',
        'name': '',
        'img': '',
        'price': '',
        'description': '',
    }
    soup = BeautifulSoup(page, 'html.parser')
    for link in soup.find_all(
            "div", {'class': re.compile(r'^iva-item-content')}, limit=1):
        try:
            result = link.find('div', {
                'class': re.compile(r'^iva-item-description')
            }).text
            if len(result.split(' ')) > MAX_DESCRIPTION_WORDS_LENGTH:
                new = ' '.join(
                    result.split(' ')[:MAX_DESCRIPTION_WORDS_LENGTH]
                )
                info['description'] = new + "..."
            else:
                info['description'] = result
        except Exception:
            error_message = "Не удалось получить описание"
            logger.error(error_message)
            info['description'] = error_message

        try:
            info['price'] = link.find(
                'meta', {'itemprop': 'price'})['content']
        except Exception:
            error_message = "Не удалось получить цену"
            logger.error(error_message)
            info['price'] = error_message

        try:
            result = link.find(
                'a', {'itemprop': 'url'})['href']
            info['link'] = f"{BASE_URL}{result}"
        except Exception:
            error_message = "Не удалось получить ссылку"
            logger.error(error_message)
            info['link'] = False

        try:
            info['name'] = link.find(
                'h3', {'itemprop': 'name'}).text
        except Exception:
            error_message = "Не удалось получить имя"
            logger.error(error_message)
            info['name'] = False

        try:
            info['img'] = link.findNext('img')['src']
        except Exception:
            error_message = "Не удалось получить картинку"
            logger.error(error_message)
            info['img'] = False

        break
    return info


def get_proxy_server_url():
    global CURR_PROXY
    if CURR_PROXY >= len(PROXIES):
        CURR_PROXY = 0
    res = PROXIES[CURR_PROXY]
    CURR_PROXY += 1
    return res


def sync_avito(url: str):
    logger.debug(f"Start parsing for: {url}")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--proxy-server={get_proxy_server_url()}')

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)

        sleep(5)
        page_source = driver.page_source

        tab_title = driver.title
        if "IP" in tab_title:
            logger.error(tab_title)
        else:
            logger.success(f"PARSED: {tab_title}")

        driver.close()
        driver.quit()
        return parse_info(page_source)
    except Exception as ex:
        logger.error(f"Selenium error: {ex}")
        driver.close()
        driver.quit()
        return None
