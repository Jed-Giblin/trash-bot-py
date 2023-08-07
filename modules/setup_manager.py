import traceback

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters
from modules.db import UnallowedBlankValue
from modules.db import db as mydb

COMMAND = "setup"

START = 1
ADD_SONARR_HOSTNAME = 11
ADD_SONARR_TOKEN = 12

ADD_RADARR_HOSTNAME = 21
ADD_RADARR_TOKEN = 22

SHARE_ACCESS = 31

ADD_SUCCESS = 'Your server has been configured. You can use the following code to share your server to ' \
              'others:'


async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        [
            InlineKeyboardButton("Add Sonarr", callback_data="add_sonarr"),
            InlineKeyboardButton("Add Radarr", callback_data="add_radarr"),
            InlineKeyboardButton("Share Access", callback_data="share_access")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(reply_keyboard)
    await update.message.reply_text(
        "Please select an action",
        reply_markup=reply_markup
    )
    return START


async def add_sonarr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.delete()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide a hostname for your server"
    )

    return ADD_SONARR_HOSTNAME


async def add_sonarr_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hostname = update.message.text
    context.user_data['tmp_sonarr_hostname'] = hostname
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide an API token for your server"
    )
    return ADD_SONARR_TOKEN


async def add_sonarr_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        share = save_configuration(update.message.from_user.id,
                                   sonarr_hostname=context.user_data['tmp_sonarr_hostname'],
                                   sonarr_token=update.message.text)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{ADD_SUCCESS} {share}'
        )
    except ValueError as ex:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"You cant setup a server with a blank {str(ex)}"
        )
    except Exception as ex:
        print("Something else went wrong")
        print(ex)
        traceback.print_exc()
    finally:
        del context.user_data['tmp_sonarr_hostname']
        return ConversationHandler.END


async def add_radarr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.delete()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide a hostname for your server"
    )

    return ADD_RADARR_HOSTNAME


async def add_radarr_hostname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hostname = update.message.text
    context.user_data['tmp_radarr_hostname'] = hostname
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide an API token for your server"
    )
    return ADD_SONARR_TOKEN


async def add_radarr_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        share = save_configuration(update.message.from_user.id,
                                   radarr_hostname=context.user_data['tmp_radarr_hostname'],
                                   radarr_token=update.message.text)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{ADD_SUCCESS} {share}'
        )
    except ValueError as ex:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"You cant setup a server with a blank {str(ex)}"
        )
    except Exception as ex:
        print("Something else went wrong")
        print(ex)
    finally:
        del context.user_data['tmp_radarr_hostname']
        return ConversationHandler.END


def save_configuration(user_id, **kwargs):
    try:
        return mydb.save_user_configuration(user_id, **kwargs)
    except UnallowedBlankValue as ex:
        raise ValueError(ex)
    except Exception as ex:
        print("Something else went wrong")
        print(ex)


async def start_share_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.delete()

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Please enter the share code you want to use"
    )
    return SHARE_ACCESS


async def share_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    share_code = update.message.text
    if mydb.share_code_is_valid(share_code):
        mydb.share_access(update.message.from_user.id, share_code)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Your share request has been configured"
        )
    else:
        await context.bot.send_message(
            chat_id=update.message.from_user.id,
            text="Unable to find that share code"
        )

    return ConversationHandler.END


CONVERSATION = ConversationHandler(
    entry_points=[CommandHandler("config", entry_point)],
    states={
        START: [
            CallbackQueryHandler(add_sonarr, pattern="^add_sonarr"),
            CallbackQueryHandler(add_radarr, pattern="^add_radarr"),
            CallbackQueryHandler(start_share_access, pattern="^share_access"),
        ],
        ADD_SONARR_HOSTNAME: [
            MessageHandler(filters=filters.TEXT, callback=add_sonarr_server)
        ],
        ADD_SONARR_TOKEN: [
            MessageHandler(filters=filters.TEXT, callback=add_sonarr_token)
        ],
        ADD_RADARR_HOSTNAME: [
            MessageHandler(filters=filters.TEXT, callback=add_radarr_hostname)
        ],
        ADD_RADARR_TOKEN: [
            MessageHandler(filters=filters.TEXT, callback=add_radarr_token)
        ],
        SHARE_ACCESS: [
            MessageHandler(filters=filters.TEXT, callback=share_access)
        ]
    },
    fallbacks=[CommandHandler("config", entry_point)]
)
