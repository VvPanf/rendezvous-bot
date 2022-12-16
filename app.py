import flask
import telebot
import os
import logging
from telebot import types
from enum import Enum
from repo.pgrepo import PgRepo


class STATES(Enum):
    S_START = 0
    S_WAIT_SECOND_ID = 1    # Ожидание ввода id второго пользователя
    S_WAIT_PLAN = 2         # Ожидание ввода плана свидания
    S_WAIT_FIRST_USER = 3   # Ожидание подтверждения от первого пользователя
    S_WAIT_SECOND_USER = 4  # Ожидание подтверждения от второго пользователя
    S_NEXT_STAGE = 5        # Состояние продолжения
    S_WAIT_QUESTION = 6     # Ожидание нового вопроса

API_TOKEN = os.environ.get("BOT_TOKEN")
DB_URL = os.environ.get("DATABASE_URL")
APP_URL = os.environ.get("APP_URL")

bot = telebot.TeleBot(API_TOKEN)
repo = PgRepo(DB_URL)


@bot.message_handler(commands=["start"])
def start_command(message):
    user = message.chat.id
    if not repo.find_user(user):
        repo.save_user(user)
    repo.save_user_state(user, STATES.S_START.value)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        types.KeyboardButton("Хочу устроить свидание"),
        types.KeyboardButton("Жду приглашения")
    )
    bot.send_message(user, "Вас приветствует Рандеву бот! Выберите свою роль!", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "Хочу устроить свидание")
def first_person(message):
    first_user = message.chat.id
    if not repo.find_user(first_user):
        repo.save_user(first_user)
    repo.save_user_state(first_user, STATES.S_WAIT_SECOND_ID.value)
    bot.send_message(first_user, "Введите user_id вашего партнёра", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(func=lambda message: message.text == "Жду приглашения")
def first_person(message):
    second_user = message.chat.id
    if not repo.find_user(second_user):
        repo.save_user(second_user)
    repo.save_user_state(second_user, STATES.S_WAIT_FIRST_USER.value)
    bot.send_message(second_user, "Ваш партнёр уже работает над приглашением!", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(func=lambda message: repo.find_user(message.chat.id)["state"] == STATES.S_WAIT_SECOND_ID.value, content_types=["text"])
def enter_second_user_id(message):
    first_user = message.chat.id
    first = repo.find_user(first_user)
    second = repo.find_user(message.text)
    if second is None:
        bot.send_message(first_user, "Пользователь не найден", reply_markup=types.ReplyKeyboardRemove())
        return
    repo.save_new_rendezvous(first["id"], second["id"])
    repo.save_user_state(first_user, STATES.S_WAIT_PLAN.value)
    bot.send_message(first_user, "Введите план свидания", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(func=lambda message: repo.find_user(message.chat.id).get("state") == STATES.S_WAIT_PLAN.value, content_types=["text"])
def enter_plan(message):
    first_user = message.chat.id
    if not validate_plan(message.text):
        bot.send_message(first_user, "План введён в неверном формате. Повторите попытку", reply_markup=types.ReplyKeyboardRemove())
    repo.save_user_state(first_user, STATES.S_WAIT_SECOND_USER.value)
    first = repo.find_user(first_user)
    plan = parse_plan(message.text)
    repo.save_rendezvous_plan(first["id"], message.text, len(plan), 0)
    second_user = repo.find_rendezvous_by_first(first_user)["second"]
    bot.send_message(first_user, "Ожидание подтверждения от второго пользователя", reply_markup=types.ReplyKeyboardRemove())
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Принять"))
    bot.send_message(second_user, "Вас пригласили на свидание", reply_markup=keyboard)


@bot.message_handler(func=lambda message: repo.find_user(message.chat.id).get("state") == STATES.S_WAIT_FIRST_USER.value and message.text == "Принять")
def accept(message):
    second_user = message.chat.id
    first_user = repo.find_rendezvous_by_second(second_user)["first"]
    repo.save_user_state(first_user, STATES.S_NEXT_STAGE.value)
    repo.save_user_state(second_user, STATES.S_WAIT_QUESTION.value)
    bot.send_message(first_user, "Ваше приглашение принято!", reply_markup=types.ReplyKeyboardRemove())
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Начать!"))
    bot.send_message(first_user, "Нажмите кнопку, когда будете готовы начать свидание", reply_markup=keyboard)


@bot.message_handler(func=lambda message: repo.find_user(message.chat.id).get("state") == STATES.S_NEXT_STAGE.value and message.text in ("Начать!", "Продолжить"), content_types=["text"])
def start_rendezvous(message):
    first_user = message.chat.id
    rendezvous = repo.find_rendezvous_by_first(first_user)
    second_user = rendezvous["second"]
    curr_stage = rendezvous["current_stage"]
    plan = parse_plan(rendezvous["plan"])
    if curr_stage >= rendezvous["stage_count"]:
        bot.send_message(second_user, "План свидания подошёл к концу! Вам понравилось?", reply_markup=types.ReplyKeyboardRemove())
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Завершить"))
        bot.send_message(first_user, "План свидания подошёл к концу! Вам понравилось?", reply_markup=keyboard)
        return
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        types.KeyboardButton(plan[curr_stage]["logo1"]),
        types.KeyboardButton(plan[curr_stage]["logo2"]),
    )
    bot.send_message(second_user, plan[curr_stage]["question"], reply_markup=keyboard)
    bot.send_message(first_user, "Ваш партнёр делает выбор...", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(func=lambda message: repo.find_user(message.chat.id).get("state") == STATES.S_WAIT_QUESTION.value, content_types=["text"])
def start_rendezvous(message):
    second_user = message.chat.id
    choice = message.text
    rendezvous = repo.find_rendezvous_by_second(second_user)
    first_user = rendezvous["first"]
    plan = parse_plan(rendezvous["plan"])
    curr_stage = rendezvous["current_stage"]
    if curr_stage >= rendezvous["stage_count"]:
        bot.send_message(second_user, "План свидания подошёл к концу! Вам понравилось?", reply_markup=types.ReplyKeyboardRemove())
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Завершить"))
        bot.send_message(first_user, "План свидания подошёл к концу! Вам понравилось?", reply_markup=keyboard)
        return
    if plan[curr_stage]["logo1"] == choice:
        choice_num = "1"
    elif plan[curr_stage]["logo2"] == choice:
        choice_num = "2"
    else:
        bot.send_message(second_user, "Неизвестный выбор")
        return
    first = repo.find_user(first_user)
    repo.save_rendezvous_current_stage(first["id"], curr_stage + 1)
    bot.send_message(second_user, "Вы выбрали вариант: " + plan[curr_stage]["answer" + choice_num], reply_markup=types.ReplyKeyboardRemove())
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Продолжить"))
    bot.send_message(first_user, "Ваш партнёр выбрал вариант: " + plan[curr_stage]["answer" + choice_num], reply_markup=keyboard)


@bot.message_handler(func=lambda message: repo.find_user(message.chat.id).get("state") in (STATES.S_NEXT_STAGE.value, STATES.S_WAIT_QUESTION.value) and message.text == "Завершить", content_types=["text"])
def start_rendezvous(message):
    first_user = message.chat.id
    second_user = repo.find_rendezvous_by_first(first_user)["second"]
    repo.save_user_state(first_user, STATES.S_START.value)
    repo.save_user_state(second_user, STATES.S_START.value)
    first = repo.find_user(first_user)
    repo.delete_rendezvous(first["id"])
    bot.send_message(first_user, "Свидание завершено", reply_markup=types.ReplyKeyboardRemove())
    bot.send_message(second_user, "Свидание завершено", reply_markup=types.ReplyKeyboardRemove())


def validate_plan(plan):
    plan_list = plan.strip().split("\n")
    if len(plan_list) % 3 != 0:
        return False
    for line in plan_list:
        if len(line.strip()) <= 1:
            return False
    return True


def parse_plan(plan):
    result = []
    plan_list = plan.strip().split("\n")
    for i in range(0, len(plan_list), 3):
        result.append({
            "question": plan_list[i],
            "logo1": plan_list[i+1][0],
            "answer1": plan_list[i+1][1:].strip(),
            "logo2": plan_list[i+2][0],
            "answer2": plan_list[i+2][1:].strip(),
        })
    return result


# Проверим, есть ли переменная окружения Хероку (как ее добавить смотрите ниже)
if 'IS_DEPLOYED' in list(os.environ.keys()):
    logger = telebot.logger
    telebot.logger.setLevel(logging.INFO)
    app = flask.Flask(__name__)

    @app.route('/' + API_TOKEN, methods=['POST'])
    def getMessage():
        bot.process_new_updates([telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))])
        return "!", 200

    @app.route('/')
    def webhook():
        bot.remove_webhook()
        bot.set_webhook(url=APP_URL)
        return "?", 200

else:
    bot.remove_webhook()
    print("Bot have been started.....")
    bot.polling(none_stop=True)