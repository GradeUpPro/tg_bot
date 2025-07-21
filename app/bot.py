import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from config import *
from db import *
from utils import is_valid_email, is_valid_phone
from service_list import services
import smtplib
from email.message import EmailMessage
import aiosmtplib

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главное меню
main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Узнать о нас")],
    [KeyboardButton(text="Решить проблему")],
    [KeyboardButton(text="Выбрать услугу")]
], resize_keyboard=True)

# Состояния
class Form(StatesGroup):
    name = State()
    inn = State()
    problem = State()
    contact_method = State()
    contact_value = State()
    choosing_service_group = State()
    choosing_service_name = State()

user_data = {}

# === START ===
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Продолжить", callback_data="agree")]
    ])
    print(message.from_user.id)
    await message.answer(
        "Нажимая кнопку 'Продолжить', Вы даете согласие на обработку "
        "<a href='https://disk.yandex.ru/i/Ada9irIV_SlEZw'>персональных данных</a>.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "agree")
async def on_agree(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Привет! Я - бот Грейди. Помогаю бизнесу системно развиваться.\n\n"
        "Как я могу к Вам обращаться?",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Form.name)

@dp.message(Form.name)
async def get_name_response(message: types.Message, state: FSMContext):
    await save_name(message.from_user.id, message.text)
    await state.clear()
    await message.answer(f"Рады знакомству, {message.text}!", reply_markup=main_menu)

# Главное меню
@dp.message(F.text == "Главное меню")
async def go_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu)

@dp.message(F.text == "Узнать о нас")
async def about_us(message: types.Message):
    await message.answer("Посетите наш сайт: https://www.grade-up.ru")

@dp.message(F.text == "Решить проблему")
async def resolve_problem(message: types.Message, state: FSMContext):
    await state.set_state(Form.inn)
    name = await get_name(message.from_user.id)
    user_data[message.from_user.id] = {'name': name, 'service': None}
    await message.answer(f"{name}, укажите ИНН Вашей организации",
                         reply_markup=with_main_menu())

@dp.message(F.text == "Выбрать услугу")
async def choose_service(message: types.Message, state: FSMContext):
    await state.set_state(Form.choosing_service_group)
    name = await get_name(message.from_user.id)
    user_data[message.from_user.id] = {'name': name}
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=group)] for group in services.keys()] +
                 [[KeyboardButton(text="Главное меню")]],
        resize_keyboard=True
    )
    await message.answer("Выберите группу услуг:", reply_markup=markup)

@dp.message(Form.choosing_service_group)
async def choose_group(message: types.Message, state: FSMContext):
    group = message.text
    if group not in services:
        await message.answer("Пожалуйста, выберите группу из списка.")
        return
    await state.set_state(Form.choosing_service_name)
    user_data[message.from_user.id]["group"] = group
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=s)] for s in services[group]] +
                 [[KeyboardButton(text="Главное меню")]],
        resize_keyboard=True
    )
    await message.answer("Выберите услугу:", reply_markup=markup)

@dp.message(Form.choosing_service_name)
async def choose_service_name(message: types.Message, state: FSMContext):
    service = message.text
    user_data[message.from_user.id]["service"] = service
    await state.set_state(Form.inn)
    await message.answer("Укажите ИНН Вашей организации", reply_markup=with_main_menu())

@dp.message(Form.inn)
async def get_inn(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not len(message.text) in [10, 12]:
        await message.answer("ИНН должен содержать только цифры (10 или 12)")
        return
    user_data[message.from_user.id]["inn"] = message.text
    await state.set_state(Form.problem)
    await message.answer("Опишите проблему, которую необходимо решить", reply_markup=with_main_menu())

@dp.message(Form.problem)
async def get_problem(message: types.Message, state: FSMContext):
    if not message.text or message.content_type != 'text':
        await message.answer("Пожалуйста, опишите проблему в виде текста.")
        return
    user_data[message.from_user.id]["problem"] = message.text
    await state.set_state(Form.contact_method)
    await message.answer("Передаю Ваше обращение  эксперту нашей компании.\nУкажите свой телефон или почту, по которой наш сотрудник сможет с Вами связаться", reply_markup=contact_method_selection())

@dp.message(Form.contact_method)
async def choose_contact_method(message: types.Message, state: FSMContext):
    method = message.text
    if method not in ["Телефон", "Email"]:
        await message.answer("Выберите способ связи: Телефон или Email.", reply_markup=contact_method_selection())
        return
    user_data[message.from_user.id]["contact_type"] = method
    await state.set_state(Form.contact_value)
    await message.answer("Введите значение ({}):".format(method.lower()), reply_markup=with_main_menu())

@dp.message(Form.contact_value)
async def get_contact(message: types.Message, state: FSMContext):
    contact_type = user_data[message.from_user.id]["contact_type"]
    if contact_type == "Телефон" and not is_valid_phone(message.text):
        await message.answer("Телефон должен быть в формате +7 (XXX) XXX-XX-XX")
        return
    if contact_type == "Email" and not is_valid_email(message.text):
        await message.answer("Укажите корректный email")
        return

    user_data[message.from_user.id]["contact"] = message.text
    await state.clear()
    text = 'Ветка "Выбрать услугу":\n' if user_data[message.from_user.id].get("service") else 'Ветка "Решить проблему":\n'
    text += (
        f"Контактное лицо: {user_data[message.from_user.id]['name']}\n"
        f"Связаться: {user_data[message.from_user.id]['contact']}\n"
        f"ИНН: {user_data[message.from_user.id]['inn']}\n"
        f"Проблема: {user_data[message.from_user.id]['problem']}"
    )
    if service := user_data[message.from_user.id].get("service"):
        text += f"\nУслуга: {service}"

    await send_to_admins(text)
    await message.answer("Ваш запрос передан эксперту. Мы скоро свяжемся с Вами.", reply_markup=main_menu)

async def send_to_admins(text: str):
    await bot.send_message(chat_id=ADMIN_TELEGRAM_USER_ID, text=text)

    msg = EmailMessage()
    msg.set_content(text)
    msg["Subject"] = "Новый запрос от Telegram-бота"
    msg["From"] = SMTP_USER
    msg["To"] = ADMIN_EMAIL

    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASSWORD,
        use_tls=True,
    )

# Команда /cancel
@dp.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu)

# Вспомогательная клавиатура с "Главное меню"
def with_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Главное меню")]],
        resize_keyboard=True
    )

def contact_method_selection():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Телефон")],
        [KeyboardButton(text="Email")],
        [KeyboardButton(text="Главное меню")]
    ], resize_keyboard=True)