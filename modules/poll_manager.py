import datetime

import pytz
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, CallbackQueryHandler

from modules.utils import ModTypes, dm_only
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
TIMEZONE = 5
GROUP_CHAT = 6


async def send_poll(context: ContextTypes.DEFAULT_TYPE) -> None:
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

@dm_only
async def schedule_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation."""
    await update.message.reply_text(
        "Please enter a name for your poll.",
        reply_markup=ForceReply(selective=True),
    )
    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data'] = {'name': update.message.text}
    await update.message.reply_text(
        f"Please enter the poll question",
        reply_markup=ForceReply(selective=True),
    )

    return QUESTION


async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data']['question'] = update.message.text
    await update.message.reply_text(
        f"Now enter your comma separated poll answers.",
        reply_markup=ForceReply(selective=True),
    )

    return CHOICES


async def choices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data']['answers'] = update.message.text.split(',')

    await update.message.reply_text(
        "Enter comma separated days of the week you want it to run. Where 0-6 is Sun-Sat",
        reply_markup=ForceReply(selective=True),
    )
    return DAYS_OF_WEEK


async def days_of_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data']['days_of_week'] = update.message.text.split(',')
    await update.message.reply_text(
        "Enter the local time you want it to run as HH:MM. Ex: 16:30 for 4:30PM",
        reply_markup=ForceReply(selective=True),
    )
    return TIME


async def time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data']['time'] = update.message.text
    reply_keyboard = [['US/Eastern', 'US/Central', 'US/Pacific', 'UTC']]

    await update.message.reply_text(
        "Please select a timezone, or copy/paste your applicable timezone from: "
        "https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder=""
        ),
    )

    return TIMEZONE


async def timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['shared_data']['timezone'] = update.message.text
    btns = []
    for chat in context.application.persistence.get_chat_list():
        if await context.bot.getChatMember(chat_id=chat.id, user_id=update.message.from_user.id):
            full_chat = await context.bot.get_chat(chat_id=chat.id)
            if full_chat.type == "private":
                continue
            else:
                slug = full_chat.title
            btns.append(InlineKeyboardButton(slug, callback_data=f'sc_{chat}'))
    markup = [[btn] for btn in btns]
    if len(btns) == 0:
        await update.message.reply_text(
            text='It appears we are not in any chats together. Add me to the chat and do this process again.'
        )
        return ConversationHandler.END
    await update.message.reply_text(
        text='Please select a chat from the list to use',
        reply_markup=InlineKeyboardMarkup(markup)
    )

    return GROUP_CHAT


async def choose_poll_post_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.callback_query.data.split('_')[-1])
    context.chat_data.save_poll(context.user_data['shared_data'])
    # Save the poll for the user in the group
    poll = context.user_data['shared_data']
    job_id = f'{chat_id}_{poll.get("name")}'
    hour, minute = poll.get('time').split(':')
    add_poll_to_job_queue(context, chat_id, poll, job_id, hour, minute)

    await update.callback_query.message.reply_text(
        text=f'Got it. Your poll will kick off in the group chat you selected.'
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    print("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Well I think we're done here.", reply_markup=ReplyKeyboardRemove()
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
        TIMEZONE: [MessageHandler(filters.TEXT, timezone)],
        GROUP_CHAT: [CallbackQueryHandler(pattern='^sc_-?[0-9]+$', callback=choose_poll_post_location)]

    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


def add_poll_to_job_queue(context, group_id, poll, job_id, hour, minute):
    remove_job_if_exists(job_id, context)
    context.job_queue.run_daily(
        callback=send_poll,
        time=datetime.time(hour=int(hour), minute=int(minute),
                           tzinfo=pytz.timezone(poll.get('timezone', 'America/New_York'))),
        days=[int(d) for d in poll.get('days_of_week')],
        chat_id=group_id,
        name=job_id,
        data={
            'options': poll.get('answers'),
            'question': poll.get('question')
        }
    )


async def load_schedules(context: ContextTypes.DEFAULT_TYPE):
    for chat in context.application.persistence.get_chat_list():
        for poll in chat.polls:
            job_id = f'{chat.id}_{poll.get("name")}'
            hour, minute = poll.get('time').split(':')
            try:
                add_poll_to_job_queue(context, chat.id, poll, job_id, hour, minute)
            except (IndexError, ValueError):
                print(f'Oops! I couldn\'t add the job {job_id} on startup.')
    for j in context.job_queue.jobs():
        print(f'Job: {j.name} will run at {j.next_t}')


LOAD_FROM_DB = load_schedules
