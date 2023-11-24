import asyncio
from loguru import logger
from parsing.parser import sync_avito
from telegram.initializer import dp
from telegram.keyboards import item_inline_kb
from db import DBCommands


async def form_answer(user_id: int, task: dict, name: str) -> None:
    markup = await item_inline_kb(task['link'])
    text = f"Обновление для {name}!\n\n" \
           f"Название: {task['name']}\n\n" \
           f"Цена: {task['price']}р\n\n" \
           f"Описание: {task['description']}\n\n"
    try:
        await dp.bot.send_photo(
            chat_id=user_id,
            photo=f"{task['img']}",
            caption=text,
            reply_markup=markup
        )
    except Exception as exception:
        logger.critical(f'Following exception was caught: {exception}')
        await dp.bot.send_message(
            chat_id=user_id,
            text=f'Задача: {name}\n\n{text}',
            reply_markup=markup,
        )


async def is_trackable(user_id: int, workers: dict) -> bool:
    db = DBCommands()
    available_workers = 1
    if await db.is_subscriber(user_id):
        available_workers = await db.worker_quantity_check(user_id)
    if len(workers.keys()) > available_workers:
        return False
    if await db.is_alive(user_id) == 0:
        return False
    return True


async def start_tracking():
    db = DBCommands()
    while True:
        # Получаем всех активных юзеров и валидируем
        active_users = await db.get_active_users()
        for user_id in list(active_users):
            worker = await db.read_tasks(user_id)
            if not await is_trackable(user_id, worker):
                continue
            # Забираем названия задач и необходимые URL
            urls, tasks_names = list(worker.values()), list(worker.keys())
            # Формируем из них Future объект для конкурентного выполнения
            tasks = [
                asyncio.create_task(
                    asyncio.to_thread(sync_avito, url)) for url in urls
            ]
            now = dict(zip(tasks_names, await asyncio.gather(*tasks)))
            for task_name in tasks_names:
                task = now.get(task_name)
                first_result = await db.read_result(user_id, task_name)
                if task['name'] not in first_result:
                    await db.register_first_result(
                        user_id,
                        task_name,
                        task['name']
                    )
                    await form_answer(user_id, task, task_name)
                await asyncio.sleep(20)
