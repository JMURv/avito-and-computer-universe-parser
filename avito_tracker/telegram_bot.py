import asyncio
from urllib.parse import urlparse

from aiogram import executor, types
from aiogram.dispatcher import FSMContext
from telegram.States import SetWorker, DeleteWorker
from telegram.initializer import dp
from telegram.keyboards import keyboard_client, keyboard_short, inline_kb
from aiogram.utils.exceptions import PhotoAsInputFileRequired

from parsing.parser import async_avito
from data_base.crud import insert_values, read_data, delete_data, check_workers
from data_base.tracking import is_tracking_now, disable_track, \
    register_user, enable_track, register_first_result, check_first_result, update_result, kill_session, check_if_exists


async def tracking(message, worker):
    user_id = message.from_user.id
    await enable_track(user_id)
    names = list(worker.keys())
    urls = list(worker.values())
    while True:
        if await is_tracking_now(user_id) == 0:
            break
        tasks = list(map(
            lambda url: asyncio.create_task(async_avito(url)), urls))
        now = dict(zip(names, await asyncio.gather(*tasks)))
        for name in names:
            task = now.get(name)
            first_result = await check_first_result(user_id, name)
            if task['name'] != first_result:
                await update_result(user_id, name, task['name'])
                inline = await inline_kb(task['link'])
                text = f"Обновление для {name}!\n\n" \
                       f"Название: {task['name']}\n\n" \
                       f"Цена: {task['price']}р\n\n" \
                       f"Описание: {task['description']}\n\n"
                try:
                    await dp.bot.send_photo(
                        chat_id=user_id,
                        photo=f"{task['img']}",
                        caption=text,
                        reply_markup=inline
                    )
                except PhotoAsInputFileRequired:
                    await dp.bot.send_message(
                        chat_id=user_id,
                        text=f'Задача: {name}\n\n{text}',
                        reply_markup=inline
                    )
        await asyncio.sleep(600)


async def worker_validator(message, worker):
    if len(worker.keys()) == 0:
        return await message.answer(
            'У Вас нет ни одного объявления --> '
            'Запуск невозможен',
            reply_markup=keyboard_client)
    if len(worker.keys()) > 5:
        return await message.answer(
            'У Вас более 5 объявлений! --> '
            'Запуск невозможен',
            reply_markup=keyboard_client)
    if await check_if_exists(message.from_user.id):
        await message.answer('Нашёл у Вас активные объявления, перезапуск...',
                             reply_markup=keyboard_short)
        return await tracking(message, worker)


@dp.message_handler(commands=['start_track'])
async def calculate_first_result(message):
    user_id = message.from_user.id
    worker = await read_data(user_id)
    await worker_validator(message, worker)
    await message.answer('Запоминаем текущее объявление..',
                         reply_markup=keyboard_short)
    urls = list(worker.values())
    names = list(worker.keys())
    tasks = list(map(
        lambda url: asyncio.create_task(async_avito(url)), urls))
    first_results = dict(zip(names, await asyncio.gather(*tasks)))
    for task in names:
        await register_first_result(user_id, task, first_results[task]['name'])
    await message.answer(
        'Запомнили!\n'
        'Включаем слежение..')
    await tracking(message, worker)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    is_registered = await register_user(message.from_user.id)
    if not is_registered:
        await message.answer("Привет 👋\n"
                             "Я бот, который следит за объявлениями за тебя!\n"
                             "Прочитай правила и FAQ перед использованием:"
                             " /help",
                             reply_markup=keyboard_client)
    else:
        name = message.from_user.username
        await message.answer(f"С возвращением, {name} 👋\n"
                             "Я тебя помню! Как дела?",
                             reply_markup=keyboard_client)


@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    await message.answer("FAQ:\n"
                         "1. Сколько я могу завести объявлений?\n"
                         "Ответ: Не более 5 объявлений.\n\n"
                         "2. Какая ссылка требуется для трекинга?\n"
                         "Ответ: Ссылка из поиска авито. "
                         "Можно настраивать всё, что предлагает сервис: "
                         "цену, доставку и тд.\n"
                         "Главное, что Вам нужно сделать - "
                         "установить сортировку по дате.\n\n"
                         "Предупреждение:\n"
                         "Остановка слежения может иметь задержку.",
                         reply_markup=keyboard_client)


@dp.message_handler()
async def reply_text(message: types.Message):
    if message.text == '✅ Добавить задачу':
        await set_worker(message)
    if message.text == '❌ Удалить задачу':
        await delete_worker(message)
    if message.text == '📋 Мои задачи':
        tasks = await check_workers(message.from_user.id)
        await message.answer(f"Ваши задачи: {tasks}",
                             reply_markup=keyboard_client)

    if message.text == '📡 Запустить слежение':
        await calculate_first_result(message)
    if message.text == '⚠ Остановить слежение':
        await message.answer('Это может занять какое-то время..')
        await disable_track(message.from_user.id)
        await kill_session(message.from_user.id)
        await message.answer('Готово!',
                             reply_markup=keyboard_client)


@dp.message_handler(commands=['delete_worker'])
async def delete_worker(message: types.Message):
    """Start deleting a task"""
    await message.answer('Введи имя задачи')
    await DeleteWorker.delete_worker_name.set()


@dp.message_handler(state=DeleteWorker.delete_worker_name)
async def delete_name(message: types.Message, state: FSMContext):
    answer = message.text
    await state.update_data(set_worker_name=answer)
    data = await state.get_data()
    worker_name = data.get('set_worker_name')

    db_resp = await delete_data(message.from_user.id, worker_name)
    await message.answer(db_resp)
    await state.finish()


@dp.message_handler(commands=['new'], state="*")
async def set_worker(message: types.Message):
    """Start adding a task"""
    await message.answer('Введи имя задачи')
    await SetWorker.set_worker_name.set()


@dp.message_handler(state=SetWorker.set_worker_name)
async def get_name(message: types.Message, state: FSMContext):
    answer = message.text
    await state.update_data(set_worker_name=answer)
    await message.answer('Отправьте URL')
    await SetWorker.set_worker_url.set()


@dp.message_handler(state=SetWorker.set_worker_url)
async def get_url(message: types.Message, state: FSMContext):
    """Finish adding a task"""
    answer = message.text
    await state.update_data(set_worker_url=answer)
    data = await state.get_data()
    name = data.get('set_worker_name')
    url = data.get('set_worker_url')

    if not url_validator(url):
        await state.finish()
        return await message.answer('Неправильный URL')

    await message.answer(f'Добавляем {name} в нашу базу..')
    await insert_values(message.from_user.id, f"'{name}'", f"'{url}'")
    await message.answer('Отлично!\n'
                         'Введите /start_track, чтобы начать слежение\n '
                         'Добавить задачу, чтобы добавить еще одно объявление')
    await state.finish()


async def url_validator(url):
    if type(url) is not str:
        return False
    if urlparse(url).netloc not in ('www.avito.ru', 'm.avito.ru'):
        return False
    return True


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
