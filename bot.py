import os
import logging
import httpx
import pickle

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

from api_client import ApiClient, API_URL

try:
    with open('intent_model.pkl', 'rb') as f:
        model = pickle.load(f)
    print("ML модель успешно загружена.")
except FileNotFoundError:
    print("Файл модели 'intent_model.pkl' не найден. Запустите train_model.py для обучения.")
    model = None

api = ApiClient(API_URL)

# Настройка логирования
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я ваш личный менеджер задач. Используйте /help для просмотра команд.")
    logger.info(f"User {update.effective_user.id} started the bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "<b>Доступные команды:</b>\n"
        "/add <i>[текст задачи]</i> - Добавить новую задачу\n"
        "/list - Показать все ваши задачи\n"
        "/edit <i>[ID] [новый текст]</i> - Изменить текст задачи\n"
        "/clear - Удалить все ваши задачи"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите текст задачи после команды.\nНапример: <code>/add Купить молоко</code>", parse_mode='HTML')
        return
    
    title = ' '.join(context.args)
    try:
        await api.add_task(user_id, title)
        await update.message.reply_text("✅ Задача успешно добавлена!")
        logger.info(f"User {user_id} added task: {title}")
    except httpx.HTTPStatusError as e:
        logger.error(f"API Error for user {user_id} on add: {e}")
        await update.message.reply_text("❌ Не удалось добавить задачу. Возможно, сервис временно недоступен.")
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id} on add: {e}")
        await update.message.reply_text("❌ Произошла непредвиденная ошибка.")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        tasks = await api.get_tasks(user_id)
        if not tasks:
            await update.message.reply_text("У вас пока нет задач. Добавьте первую командой /add!")
            return
        
        await update.message.reply_text("<b>Ваш список задач:</b>", parse_mode='HTML')
        for task in tasks:
            message_text = f"<b>{task['id']}.</b> {task['title']}"
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Завершить / 🗑️ Удалить", callback_data=f"remove_{task['id']}")
                ]
            ])
            await update.message.reply_text(message_text, reply_markup=keyboard, parse_mode='HTML')

    except httpx.HTTPStatusError as e:
        logger.error(f"API Error for user {user_id} on list: {e}")
        await update.message.reply_text("❌ Не удалось получить список задач.")
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id} on list: {e}")
        await update.message.reply_text("❌ Произошла непредвиденная ошибка.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    action, task_id_str = query.data.split('_', 1)
    task_id = int(task_id_str)

    try:
        if action == "remove":
            await api.remove_task(user_id, task_id)
            await query.edit_message_text(f"Задача [ID: {task_id}] удалена.")
            logger.info(f"User {user_id} removed task {task_id}.")
        
        elif action == "done":
            await api.remove_task(user_id, task_id)
            await query.edit_message_text(f"Задача выполнена и убрана из списка. Отличная работа!")
            logger.info(f"User {user_id} completed task {task_id}.")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await query.edit_message_text("Эта задача уже была удалена.")
        else:
            logger.error(f"API Error for user {user_id} on button click: {e}")
            await query.edit_message_text("❌ Ошибка при выполнении действия.")
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id} on button click: {e}")
        await query.edit_message_text("❌ Произошла непредвиденная ошибка.")

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args or len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text("<b>Неправильный формат.</b>\nИспользуйте: <code>/edit [ID] [новый текст]</code>", parse_mode='HTML')
        return

    task_id = int(context.args[0])
    new_title = ' '.join(context.args[1:])
    try:
        await api.update_task_title(user_id, task_id, new_title)
        await update.message.reply_text(f"✅ Задача [ID: {task_id}] обновлена.")
        logger.info(f"User {user_id} edited task {task_id}.")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await update.message.reply_text("❌ Задача с таким ID не найдена.")
        else:
            await update.message.reply_text("❌ Ошибка при обновлении задачи.")
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id} on edit: {e}")
        await update.message.reply_text("❌ Произошла непредвиденная ошибка.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        await api.clear_tasks(user_id)
        await update.message.reply_text("✅ Все ваши задачи были удалены.")
        logger.info(f"User {user_id} cleared all tasks.")
    except httpx.HTTPStatusError as e:
        logger.error(f"API Error for user {user_id} on clear: {e}")
        await update.message.reply_text("❌ Ошибка при удалении задач.")
    except Exception as e:
        logger.error(f"Unexpected error for user {user_id} on clear: {e}")
        await update.message.reply_text("❌ Произошла непредвиденная ошибка.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Эта функция теперь использует ML-модель для распознавания намерений.
    """
    if model is None:
        await update.message.reply_text("Извините, модуль ИИ не загружен. Обратитесь к администратору.")
        return

    text = update.message.text
    
    intent = model.predict([text])[0]

    match intent:
        case "GREETING":
            await update.message.reply_text("Привет! Чем могу помочь?")
        
        case "THANKS":
            await update.message.reply_text("Всегда пожалуйста!")
            
        case "LIST_TASKS":
            await list_tasks(update, context)
            
        case "ADD_TASK":
            context.args = text.split()
            await add(update, context)
            
        case "UNKNOWN":
            await update.message.reply_text(
                "Я не совсем понял. Я умею работать со списком задач. "
                "Для помощи используйте команду /help."
            )
        
        case _:
            await update.message.reply_text("Интересная мысль, но я пока не знаю, как на это реагировать.")


if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise RuntimeError("Переменная окружения TELEGRAM_TOKEN не установлена!")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("edit", edit))
    app.add_handler(CommandHandler("clear", clear))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен с ML-моделью...")
    app.run_polling()