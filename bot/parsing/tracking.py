import time

from loguru import logger
import asyncio
from parsing.parser import sync_avito
from telegram.initializer import bot
from telegram.keyboards import item_inline_kb
from db import DBCommands


UPDATE_TEXT = """
Обновление для {task_name}!

Название: {adv_name}

Цена: {adv_price}

Описание: {adv_desc}
"""


async def form_answer(user_id, task_name, adv_name, adv_href, adv_price, adv_desc, adv_image):
    markup = await item_inline_kb(adv_href)
    logger.debug(f"Image data: {adv_image}")
    return await bot.send_message(
        chat_id=user_id,
        text=UPDATE_TEXT.format(
            task_name=task_name,
            adv_name=adv_name,
            adv_price=adv_price,
            adv_desc=adv_desc
        ),
        reply_markup=markup,
    )


async def is_trackable(user_id: int, tasks_quantity: int) -> bool:
    db = DBCommands()
    available_workers = 1
    if await db.is_subscriber(user_id):
        available_workers = await db.worker_quantity_check(user_id)
    if tasks_quantity > available_workers:
        return False
    if await db.is_alive(user_id) == 0:
        return False
    return True


async def start_tracking():
    """
    Функция забирает активные задачи для каждого пользователя
    и формирует из них Future объект для ПОСЛЕДОВАТЕЛЬНОГО выполнения
    Это обусловлено возможностью получить бан по IP на авито
    """
    db = DBCommands()
    while True:
        active_users = await db.get_active_users()
        for user_id in list(active_users):
            tasks = await db.read_tasks(user_id)
            if not await is_trackable(user_id=user_id, tasks_quantity=len(tasks.keys())):
                continue
            for task_name, task_url in tasks.items():
                result = await asyncio.create_task(
                    asyncio.to_thread(sync_avito, task_url)
                )
                if result:
                    adv_name = result.get("name")
                    adv_price = result.get("price")
                    adv_href = result.get("link")
                    adv_desc = result.get("description")
                    adv_image = result.get('img')
                    first_result = await db.read_result(user_id, task_name)
                    if all([adv_name, adv_href]) and adv_name not in first_result:
                        logger.debug("Найдено новое объявление")
                        await db.register_first_result(
                            user_id,
                            task_name,
                            result.get('name')
                        )
                        await form_answer(
                            user_id=user_id,
                            task_name=task_name,
                            adv_name=adv_name,
                            adv_href=adv_href,
                            adv_price=adv_price,
                            adv_desc=adv_desc,
                            adv_image=adv_image,
                        )
                time.sleep(20)
