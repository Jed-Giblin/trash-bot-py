import datetime

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler

from modules.utils import ModTypes
from modules.db import db as mydb
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import uuid

MOD_TYPE = ModTypes.CONVERSATION

NAME = 0
QUESTION = 1
CHOICES = 2
DAYS_OF_WEEK = 3
TIME = 4


async def poll(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a predefined poll"""
    job = context.job
    await context.bot.send_poll(
        job.chat_id,
        job.data.get('question'),
        job.data.get('options'),
        is_anonymous=False,
        allows_multiple_answers=False,
    )


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def schedule_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation."""
    reply_keyboard = [[]]

    await update.message.reply_text(
        "Please enter a name for your poll.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="When should we do that thing?"
        ),
    )

    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data'] = {'name': update.message.text}
    reply_keyboard = [[]]
    await update.message.reply_text(
        f"Please enter the poll question",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder=""
        ),
    )

    return QUESTION


async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data']['question'] = update.message.text
    reply_keyboard = [[]]
    await update.message.reply_text(
        f"Now enter your comma separated poll answers.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder=""
        ),
    )

    return CHOICES


async def choices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data']['answers'] = update.message.text.split(',')
    reply_keyboard = [[]]

    await update.message.reply_text(
        "Enter comma separated days of the week you want it to run. Where 0-6 is Sun-Sat",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder=""
        ),
    )
    return DAYS_OF_WEEK


async def days_of_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data']['days_of_week'] = update.message.text.split(',')
    reply_keyboard = [[]]

    await update.message.reply_text(
        "Enter the utc time you want it to run as HH:MM. Ex: 16:30 for 4:30PM",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder=""
        ),
    )
    return TIME


async def time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data']['time'] = update.message.text
    chat_id = str(update.effective_message.chat_id)
    if not mydb.get_group(chat_id):
        mydb.db['groups'] = {chat_id: {}}
    if 'polls' not in mydb.db['groups'][chat_id]:
        mydb.db['groups'][chat_id] = {'polls': []}
    # Save the poll for the user in the group
    mydb.db['groups'][chat_id]['polls'].append(context.user_data['shared_data'])
    mydb.save_group(group_id=chat_id, **mydb.db['groups'][chat_id])

    await update.message.reply_text("Your automated poll has been created.")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    print("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


CONVERSATION = ConversationHandler(
    entry_points=[CommandHandler("schedule_poll", schedule_poll)],
    states={
        NAME: [MessageHandler(filters.TEXT, name)],
        QUESTION: [MessageHandler(filters.TEXT, question)],
        CHOICES: [MessageHandler(filters.TEXT, choices)],
        DAYS_OF_WEEK: [MessageHandler(filters.TEXT, days_of_week)],
        TIME: [MessageHandler(filters.TEXT, time)],

    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


async def load_schedules(context: ContextTypes.DEFAULT_TYPE):
    for group_id in mydb.db['groups']:
        for poll in mydb.db['groups'][group_id].get('polls', []):
            job_id = f'{group_id}_{poll.get("name")}'
            hour, minute = poll.get('time').split(':')
            try:
                remove_job_if_exists(job_id, context)
                context.job_queue.run_daily(
                    callback=poll,
                    time=datetime.time(hour=int(hour), minute=int(minute)),
                    days=[int(d) for d in poll.get('days_of_week')],
                    chat_id=group_id,
                    name=job_id,
                    data={
                        'options': poll.get('answers'),
                        'question': poll.get('question')
                    }
                )

            except (IndexError, ValueError):
                print('Oops!')
    for j in context.job_queue.jobs():
        print(j.next_t)


LOAD_FROM_DB = load_schedules
