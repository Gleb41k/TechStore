import asyncio
import json
import os
from datetime import datetime
import pandas as pd
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = "7291750450:AAGF4rRtaJPjo8IDDEYw9ciF3mSc6mGhkrA"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

USERS_FILE = "users.json"
PROFILES_FILE = "profiles.json"
FAVORITES_FILE = "favorites.json"
ORDERS_FILE = "orders.xlsx"
mailing_state = {}


# === Классы состояний ===
class ProfileStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_address = State()


# === Работа с пользователями ===
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False)


def load_profiles():
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_profiles(profiles):
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False)


def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_favorites(favorites):
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False)


def save_order_to_excel(user_id, profile, order_data):
    """Сохранение заказа в Excel файл"""
    order_info = {
        "ID пользователя": user_id,
        "Дата заказа": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Имя": profile.get("name", ""),
        "Телефон": profile.get("phone", ""),
        "Email": profile.get("email", ""),
        "Адрес": profile.get("address", ""),
        "Товары": order_data.get("items", ""),
        "Количество товаров": order_data.get("item_count", 0),
        "Сумма": order_data.get("total", 0),
        "Способ оплаты": order_data.get("payment", ""),
        "Комментарий": order_data.get("comment", ""),
        "Статус": "Новый"
    }

    df = pd.DataFrame([order_info])

    if os.path.exists(ORDERS_FILE):
        existing_df = pd.read_excel(ORDERS_FILE)
        df = pd.concat([existing_df, df], ignore_index=True)

    df.to_excel(ORDERS_FILE, index=False)


# === /start ===
@router.message(Command("start"))
async def start(message: Message):
    users = load_users()
    if message.from_user.id not in users:
        users.append(message.from_user.id)
        save_users(users)

    # Проверяем есть ли профиль
    profiles = load_profiles()
    user_profile = profiles.get(str(message.from_user.id))

    if user_profile:
        # Показываем главное меню с профилем
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍️ Магазин", web_app=WebAppInfo(url="https://gleb1.b3654yy2.beget.tech/"))],
            [InlineKeyboardButton(text="❤️ Избранное", callback_data="favorites")],
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
        ])
        await message.answer(
            f"👋 Добро пожаловать, {user_profile.get('name', message.from_user.first_name)}!\n\n"
            "Выберите раздел:",
            reply_markup=kb
        )
    else:
        # Предлагаем создать профиль
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍️ Магазин", web_app=WebAppInfo(url="https://gleb1.b3654yy2.beget.tech/"))],
            [InlineKeyboardButton(text="👤 Создать профиль", callback_data="create_profile")]
        ])
        await message.answer(
            f"Привет, {message.from_user.first_name}! Для полного доступа к функциям создайте профиль.",
            reply_markup=kb
        )


# === Профиль ===
@router.callback_query(F.data == "create_profile")
async def create_profile_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_name)
    await call.message.answer("Введите ваше ФИО:")


@router.message(ProfileStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ProfileStates.waiting_for_phone)
    await message.answer("Введите ваш телефон:")


@router.message(ProfileStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(ProfileStates.waiting_for_email)
    await message.answer("Введите ваш email:")


@router.message(ProfileStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    await state.set_state(ProfileStates.waiting_for_address)
    await message.answer("Введите адрес доставки (Страна, Город, Улица, Дом, Квартира):")


@router.message(ProfileStates.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    data = await state.get_data()

    # Сохраняем профиль
    profiles = load_profiles()
    profiles[str(message.from_user.id)] = {
        "name": data.get("name"),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "address": data.get("address"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_profiles(profiles)

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍️ Магазин", web_app=WebAppInfo(url="https://gleb1.b3654yy2.beget.tech/"))],
        [InlineKeyboardButton(text="❤️ Избранное", callback_data="favorites")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])

    await message.answer(
        "✅ Профиль успешно создан!\n\n"
        f"👤 ФИО: {data.get('name')}\n"
        f"📱 Телефон: {data.get('phone')}\n"
        f"📧 Email: {data.get('email')}\n"
        f"📍 Адрес: {data.get('address')}\n\n"
        "Теперь вы можете добавлять товары в избранное и оформлять заказы.",
        reply_markup=kb
    )


@router.callback_query(F.data == "profile")
async def view_profile(call: CallbackQuery):
    profiles = load_profiles()
    user_profile = profiles.get(str(call.from_user.id))

    if user_profile:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile")],
            [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ])

        await call.message.answer(
            "👤 **Ваш профиль:**\n\n"
            f"**ФИО:** {user_profile.get('name')}\n"
            f"**Телефон:** {user_profile.get('phone')}\n"
            f"**Email:** {user_profile.get('email')}\n"
            f"**Адрес:** {user_profile.get('address')}\n"
            f"**Дата регистрации:** {user_profile.get('created_at')}",
            parse_mode="Markdown",
            reply_markup=kb
        )
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Создать профиль", callback_data="create_profile")]
        ])
        await call.message.answer("Профиль не найден. Создайте профиль:", reply_markup=kb)


# === Избранное ===
@router.callback_query(F.data == "favorites")
async def view_favorites(call: CallbackQuery):
    favorites = load_favorites()
    user_favorites = favorites.get(str(call.from_user.id), [])

    if user_favorites:
        favorites_text = "\n".join([f"❤️ {item}" for item in user_favorites])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍️ Перейти в магазин",
                                  web_app=WebAppInfo(url="https://gleb1.b3654yy2.beget.tech/"))],
            [InlineKeyboardButton(text="🗑️ Очистить избранное", callback_data="clear_favorites")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ])
        await call.message.answer(
            f"❤️ **Ваше избранное:**\n\n{favorites_text}",
            parse_mode="Markdown",
            reply_markup=kb
        )
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍️ Перейти в магазин",
                                  web_app=WebAppInfo(url="https://gleb1.b3654yy2.beget.tech/"))],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ])
        await call.message.answer(
            "Ваше избранное пусто. Добавьте товары из магазина!",
            reply_markup=kb
        )


# === Оформление заказа (имитация) ===
@router.callback_query(F.data == "checkout_demo")
async def checkout_demo(call: CallbackQuery):
    profiles = load_profiles()
    user_profile = profiles.get(str(call.from_user.id))

    if not user_profile:
        await call.message.answer("Сначала создайте профиль для оформления заказа.")
        return

    # Имитация данных заказа (в реальности будут приходить из магазина)
    order_summary = (
        "**Оформление заказа**\n\n"
        "**Получатель**\n"
        f"👤 {user_profile.get('name')}\n\n"

        "**Доставка**\n"
        "🚚 Курьером по адресу\n"
        f"📍 {user_profile.get('address')}\n"
        "📦 Пункты выдачи: доступны при выборе\n\n"

        "**Оплата**\n"
        "💳 При получении\n\n"

        "**Промокод**\n"
        "🎟️ Введите промокод\n\n"

        "**Комментарий к заказу**\n"
        "✏️ Добавьте комментарий\n\n"

        "**Ваш заказ**\n"
        "📦 2 товара    80 200 ₽\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**Итого:    80 200 ₽**\n\n"

        "Нажимая на кнопку 'Оформить заказ', я соглашаюсь на обработку персональных данных."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit_order")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])

    await call.message.answer(order_summary, parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data == "confirm_order")
async def confirm_order(call: CallbackQuery):
    profiles = load_profiles()
    user_profile = profiles.get(str(call.from_user.id))

    # Имитация данных заказа
    order_data = {
        "items": "Товар 1, Товар 2",
        "item_count": 2,
        "total": 80200,
        "payment": "При получении",
        "comment": "Комментарий к заказу"
    }

    # Сохраняем заказ в Excel
    save_order_to_excel(call.from_user.id, user_profile, order_data)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍️ Продолжить покупки",
                              web_app=WebAppInfo(url="https://gleb1.b3654yy2.beget.tech/"))],
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")]
    ])

    await call.message.answer(
        "✅ **Заказ успешно оформлен!**\n\n"
        "Номер заказа: #" + datetime.now().strftime("%Y%m%d%H%M%S") + "\n"
                                                                      "Сумма: 80 200 ₽\n"
                                                                      "Способ оплаты: При получении\n"
                                                                      "Статус: Обрабатывается\n\n"
                                                                      "С вами свяжется наш менеджер для подтверждения заказа.",
        parse_mode="Markdown",
        reply_markup=kb
    )


@router.callback_query(F.data == "my_orders")
async def my_orders(call: CallbackQuery):
    if os.path.exists(ORDERS_FILE):
        try:
            df = pd.read_excel(ORDERS_FILE)
            user_orders = df[df['ID пользователя'] == call.from_user.id]

            if not user_orders.empty:
                orders_text = ""
                for _, order in user_orders.iterrows():
                    orders_text += (
                        f"\n📦 **Заказ #{order.name}**\n"
                        f"Дата: {order['Дата заказа']}\n"
                        f"Товары: {order['Товары']}\n"
                        f"Сумма: {order['Сумма']} ₽\n"
                        f"Статус: {order['Статус']}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                    )

                await call.message.answer(
                    f"📋 **История ваших заказов:**{orders_text}",
                    parse_mode="Markdown"
                )
            else:
                await call.message.answer("У вас пока нет заказов.")
        except:
            await call.message.answer("У вас пока нет заказов.")
    else:
        await call.message.answer("У вас пока нет заказов.")


# === Настройки (админ) ===
@router.callback_query(F.data == "settings")
async def settings(call: CallbackQuery):
    # Проверяем админские права (можно добавить проверку по ID)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Управление товарами", callback_data="manage_products")],
        [InlineKeyboardButton(text="👥 База клиентов", callback_data="view_users")],
        [InlineKeyboardButton(text="📊 Заказы (Excel)", callback_data="view_orders_excel")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="start_mailing")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])

    await call.message.answer("⚙️ **Меню настроек:**", parse_mode="Markdown", reply_markup=kb)


@router.callback_query(F.data == "view_orders_excel")
async def view_orders_excel(call: CallbackQuery):
    if os.path.exists(ORDERS_FILE):
        await call.message.answer(
            f"📊 **Файл с заказами создан:**\n\n"
            f"📁 Файл: `{ORDERS_FILE}`\n"
            f"📅 Последнее обновление: {datetime.fromtimestamp(os.path.getmtime(ORDERS_FILE)).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "В файле содержатся все заказы пользователей.",
            parse_mode="Markdown"
        )
    else:
        await call.message.answer("Файл с заказами пока не создан.")


# === Рассылка ===
@router.callback_query(F.data == "start_mailing")
async def start_mailing(call: CallbackQuery):
    mailing_state[call.from_user.id] = {}
    await call.message.answer("✏️ Введите текст рассылки:")


@router.message(lambda msg: msg.from_user.id in mailing_state and "pending" not in mailing_state[msg.from_user.id])
async def mailing_text_received(message: Message):
    mailing_state[message.from_user.id]["pending"] = message.text

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="send_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="send_no")
        ]
    ])

    await message.answer(
        f"**Предпросмотр рассылки:**\n\n{message.text}\n\nОтправить всем пользователям?",
        parse_mode="Markdown",
        reply_markup=kb
    )


@router.callback_query(F.data == "send_yes")
async def send_yes(call: CallbackQuery):
    text = mailing_state[call.from_user.id]["pending"]
    users = load_users()

    sent_count = 0
    for u in users:
        try:
            await bot.send_message(u, text)
            sent_count += 1
        except:
            pass

    del mailing_state[call.from_user.id]
    await call.message.answer(f"📩 Рассылка отправлена {sent_count}/{len(users)} пользователям.")


@router.callback_query(F.data == "send_no")
async def send_no(call: CallbackQuery):
    del mailing_state[call.from_user.id]
    await call.message.answer("❌ Рассылка отменена. Введите текст заново.")


# === База клиентов ===
@router.callback_query(F.data == "view_users")
async def view_users(call: CallbackQuery):
    users = load_users()
    profiles = load_profiles()

    registered_count = sum(1 for uid in users if str(uid) in profiles)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Скачать отчет (Excel)", callback_data="download_report")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings")]
    ])

    await call.message.answer(
        f"👥 **Статистика клиентов:**\n\n"
        f"• Всего пользователей: {len(users)}\n"
        f"• С профилем: {registered_count}\n"
        f"• Без профиля: {len(users) - registered_count}",
        parse_mode="Markdown",
        reply_markup=kb
    )


# === Кнопка назад ===
@router.callback_query(F.data == "back_to_main")
async def back_to_main(call: CallbackQuery):
    await start(call.message)


# === Команда /id ===
@router.message(lambda msg: msg.text.lower() in ["/id", "id"])
async def get_id(message: Message):
    await message.answer(
        f"👋 Здравствуйте, {message.from_user.first_name}!\n"
        f"🆔 Ваш ID: `{message.from_user.id}`",
        parse_mode="Markdown"
    )


# === Запуск ===
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Создаем необходимые файлы при первом запуске
    if not os.path.exists(USERS_FILE):
        save_users([])
    if not os.path.exists(PROFILES_FILE):
        save_profiles({})
    if not os.path.exists(FAVORITES_FILE):
        save_favorites({})

    print("Бот запущен!")
    asyncio.run(main())