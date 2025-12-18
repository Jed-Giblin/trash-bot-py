import datetime
import logging
import inspect
import tempfile
from pathlib import Path
import os
import pytz
import requests
import telegram.error
import datetime
from O365 import Account
from openpyxl.worksheet.worksheet import Worksheet
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, Application, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters
from modules.utils import ModTypes, premium_chat_whitelist, premium_only, dm_only, update_user, not_in_support
from openpyxl import load_workbook

MOD_TYPE = ModTypes.CONVERSATION
logger = logging.getLogger('Trash')
START = 1
END = 2

FILE_PATH = os.getenv('FILE_PATH')
SITE_PATH = os.getenv('SITE_PATH')


@premium_only
@not_in_support
async def who_is_on_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    week = datetime.datetime.now(pytz.timezone('America/New_York')).date().isocalendar().week
    today = datetime.datetime.now()
    today_str = today.strftime('%Y-%m-%d 00:00:00')
    try:
        # Its the week number minus 2 (Header Row, Missing first year)
        record = context.chat_data.oc_sched[week - 1]
        im_record = None
        for item in context.chat_data.im_oc:
            if str(item[2]) == today_str:
                im_record = item
                break
        msg = f'T3: {record[0]} is on call this week' if record else 'Good question'
        if im_record and im_record != ['None','None','None']:
            utc_ts = update.message.date
            eastern_ts = utc_ts.astimezone(pytz.timezone('America/New_York'))
            if datetime.time(7, 30) <= eastern_ts.time() <= datetime.time(19, 30):
                msg += f'\n\n\n\nIM: {im_record[0]} is on call right now as IM'
            else:
                msg += f'\n\n\n\nIM: {im_record[1]} is on call tomorrow as IM'
        await update.message.reply_text(
            text=msg
        )
    except Exception as ex:
        print(ex)


@premium_only
@dm_only
@update_user
async def oc_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main menu of the /oc command
    :param update:
    :param context:
    :return:
    """
    logger.debug(f'Firing callback: {inspect.stack()[0][3]}')
    reply_keyboard = [
        [InlineKeyboardButton("View my Schedule", callback_data="view_oc")],
        [InlineKeyboardButton("Change an OnCall", callback_data="change_oc")],
    ]
    reply_markup = InlineKeyboardMarkup(reply_keyboard)
    await update.message.reply_text(
        "Please select an action", quote=True,
        reply_markup=reply_markup
    )
    return START


async def view_oc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback when selecting "View my Schedule"
    :param update:
    :param context:
    :return:
    """
    await update.callback_query.answer()
    message = 'You are on call the following weeks:'
    for week in context.user_data.oc_sched:
        if week[-1]:
            message += f'\n{datetime.datetime.strptime(week[2], "%Y-%m-%d %H:%M:%S").date()} - {datetime.datetime.strptime(week[3], "%Y-%m-%d %H:%M:%S").date()}'
    await update.callback_query.message.reply_text(message)
    return ConversationHandler.END


async def change_oc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   message="Well I think we're done here.", reply_markup=ReplyKeyboardRemove()
                                   )

    return ConversationHandler.END



async def fetch_xls(context: ContextTypes.DEFAULT_TYPE):
    """
    Called as a job inside PyTGB to download the XLS file
    :param context:
    :return:
    """
    account = Account((os.getenv('APP_ID'), os.getenv('SECRET_ID')), tenant_id='cisco.onmicrosoft.com', auth_flow_type='credentials')
    account.authenticate()
    site = account.sharepoint().get_site(os.getenv('SITE_ID'))
    site.list_document_libraries()[0].get_item_by_path(os.getenv('FILE_PATH')).download(to_path='/tmp', name='roster.xlsx')
    await load_xls_data(context)
    # if response.status_code == 200:
    #     with open('/tmp/roster.xlsx', "wb") as lf:
    #         lf.write(response.content)
    #
    # await load_xls_data(context)

async def clean_and_setup_new_dowload(context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.run_monthly(
        callback=fetch_xls,
        day=1,
        when=datetime.time(hour=0, minute=1, second=1),
        chat_id=int(os.getenv("PREMIUM_CHAT_ID")),
        name='fetch_xls'
    )

    context.job_queue.run_once(
        callback=fetch_xls,
        when=5,
        chat_id=int(os.getenv("PREMIUM_CHAT_ID")),
        name='fetch_xls'
    )

async def load_xls_data(context: ContextTypes.DEFAULT_TYPE):
    """
    Main method for parsing data from the XLS downloaded from sharepoint.
    :param context:
    :return:
    """
    logger.info("Loading XLS Data")
    wb = load_workbook('/tmp/roster.xlsx')
    ws: Worksheet = next(filter(lambda x: x.title == os.getenv('WS_NAME'), wb.worksheets))
    context.chat_data.oc_sched = []
    context.chat_data.im_oc = []
    um = {}
    udl = context.application.user_data
    for user in udl.values():
        um[user.full_name] = user
        user.oc_sched = []

    rows = iter(ws.rows)
    next(rows)
    for row in rows:
        record = [str(c.value) for c in row[0:4]]
        print(record)
        logger.info(record)
        if datetime.datetime.strptime(record[-1],"%Y-%m-%d %H:%M:%S").date() > datetime.datetime.now().date():
            record.append(str(True))
        else:
            record.append(str(False))
        context.chat_data.oc_sched.append(record)
        if record[0] in um:
            um[record[0]].oc_sched.append(record)

    ws2: Worksheet = next(filter(lambda x: x.title == os.getenv('WS_NAME_2'), wb.worksheets))
    rows = iter(ws2.rows)
    next(rows)
    for row in rows:
        record = [str(c.value) for c in row[0:3]]
        context.chat_data.im_oc.append(record)


    await context.application.update_persistence()


CONVERSATION = ConversationHandler(
    entry_points=[CommandHandler("oc", oc_menu), CommandHandler("whoisoncall", who_is_on_call)],
    states={
        START: [
            CallbackQueryHandler(view_oc, pattern="^view_oc"),
            CallbackQueryHandler(change_oc, pattern="^change_oc")
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

LOAD_FROM_DB = clean_and_setup_new_dowload