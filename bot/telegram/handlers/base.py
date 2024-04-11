from loguru import logger
from aiogram import types
from telegram.initializer import dp, bot
from telegram.keyboards import (
    main_markup, main_menu,
)
from db import DBCommands


@dp.callback_query_handler(lambda q: q.data == main_menu)
async def return_to_main_menu(query: types.CallbackQuery):
    await send_image(
        cid=query.from_user.id,
        caption="",
        markup=await main_markup()
    )


async def send_image(cid, caption: str, markup: types.InlineKeyboardMarkup):
    with open('./data/avito_logo.png', 'rb') as photo:
        return await bot.send_photo(
            chat_id=cid,
            photo=photo,
            caption=caption,
            reply_markup=markup
        )


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    db = DBCommands()
    if not await db.create_user(message.from_user.id):
        logger.debug(f"New user registered: {message.from_user.username}")
    with open('./data/avito_logo.png', 'rb') as photo:
        return await message.answer_photo(
            photo=photo,
            caption="Главное меню",
            reply_markup=await main_markup()
        )


async def bot_start():
    await dp.skip_updates()
    await dp.start_polling(bot)
