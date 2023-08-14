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

QUESTION = 1
CHOICES = 2
CRON = 3


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


async def start_weekly_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simple schedule to run a poll every Tuesday at noon"""
    chat_id = update.effective_message.chat_id
    try:
        job_removed = remove_job_if_exists(str(chat_id), context)
        job = context.job_queue.run_daily(
            callback=poll,
            time=datetime.time(hour=16),
            days=(2,),
            chat_id=chat_id,
            name=str(chat_id),
            data={
                'options': ["Yes", "No", "Maybe"],
                'question': 'Office Wednesday?'
            }
        )
        text = "Schedule will run every Tuesday around noon!"
        if job_removed:
            text += " Old one was removed."
        await update.effective_message.reply_text(text)
        await job.run(context.application)
    except (IndexError, ValueError):
        await update.effective_message.reply_text("Oops! That didn't work.")


async def stop_weekly_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Poll schedule successfully removed!" if job_removed else "You have no active poll schedule."
    await update.message.reply_text(text)


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
        "Please submit the question for your poll.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="When should we do that thing?"
        ),
    )

    return QUESTION


async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(update.message.text)
    context.user_data['shared_data'] = {'question': update.message.text}
    reply_keyboard = [[]]
    await update.message.reply_text(
        f"Now enter your comma separated poll options.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder=""
        ),
    )

    return CHOICES


async def choices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(update.message.text)
    context.user_data['shared_data']['choices'] = update.message.text.split(',')
    reply_keyboard = [[]]

    await update.message.reply_text(
        "Enter your cron schedule for the poll. Ex: 0 12 * * 2",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder=""
        ),
    )
    return CRON


async def cron(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(update.message.text)
    await update.message.reply_text("Got it!")
    context.user_data['shared_data']['cron'] = str(update.message.text)

    chat_id = str(update.effective_message.chat_id)
    if not mydb.get_group(chat_id):
        mydb.db['groups'] = {chat_id: {}}
    if 'polls' not in mydb.db['groups'][chat_id]:
        mydb.db['groups'][chat_id] = {'polls': []}
    uid = update.message.from_user.id
    if uid not in mydb.db['groups'][chat_id]['polls']:
        mydb.db['groups'][chat_id]['polls'] = {uid: []}
    # Save the poll for the user in the group
    mydb.db['groups'][chat_id]['polls'][uid].append(context.user_data['shared_data'])
    # mydb.db.save_group(group_id=chat_id, **mydb.db['groups'][chat_id])
    return CRON


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
        QUESTION: [MessageHandler(filters.TEXT, question)],
        CHOICES: [MessageHandler(filters.TEXT, choices)],
        CRON: [MessageHandler(filters.TEXT, cron)],

    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


async def load_schedules(context: ContextTypes.DEFAULT_TYPE):
    print("In this method, cycle through the jobs defined in the DB")
    print("As you do, add them to the job queue with appropriate frequency")
    print("I would probably change how you gather the job data and save it something like")
    print( "{ groups: { 123123123: { polls: [ { 'name': 'Dumb', 'Question': '', 'Answers': [], 'days_of_week': [], 'time': ''")
    print(context.job_queue.jobs())


LOAD_FROM_DB = load_schedules
