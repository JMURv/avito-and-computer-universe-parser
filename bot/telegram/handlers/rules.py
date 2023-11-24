from aiogram.types import CallbackQuery
from aiogram.utils.exceptions import MessageNotModified

from telegram.initializer import dp
from telegram.keyboards import rules, main_markup


@dp.callback_query_handler(lambda query: query.data == rules)
async def rules_handler(query: CallbackQuery):
    rules_text = """
        ✅ | ПОКУПАЯ ЛЮБОЙ ТОВАР, ВЫ АВТОМАТИЧЕСКИ СОГЛАШАЕТЕСЬ СО ВСЕМИ ПРАВИЛАМИ!\nP.s. Не знание правил не освобождает вас от ответственности.
        ═══════════════════════════════════════════
        💯 | Гарантируем, что все товары будут куплены легальным путём в официальном магазине.
        🥸 | Гарантируем сохранность ваших персональных данных. Однако все равно рекомендуем менять пароль после завершения заказа.
        🦆 |Гарантируем обратную связь и полную поддержку до, во время и после выполнения заказа.
        🎥 | Всегда имейте запись (видеодоказательство), чтобы в случае неработоспособности мы могли выдать вам замену.
        💸 | Возврат средств за купленный товар не производим, только замена товара, в случае его неработоспособности.
        💸 | Баланс с бота не возвращаем!
        """
    try:
        await query.message.edit_caption(
            caption=rules_text,
            reply_markup=await main_markup()
        )
    except MessageNotModified:
        return
