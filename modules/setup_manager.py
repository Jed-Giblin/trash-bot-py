import pprint
import traceback
import os

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters
from modules.utils import ModTypes
from modules.readarr_api import ReadarrApi

MOD_TYPE = ModTypes.CONVERSATION

COMMAND = "setup"

START = 1
ADD_SONARR_HOSTNAME = 11
ADD_SONARR_TOKEN = 12

ADD_RADARR_HOSTNAME = 21
ADD_RADARR_TOKEN = 22

ADD_READARR_HOSTNAME = 41
ADD_READARR_TOKEN = 42

SHARE_ACCESS = 31

ADD_SUCCESS = 'Your server has been configured. You can use the following code (including the - if its there) ' \
              'to share your server to others:'


async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "That's only allowed in private chats.", quote=True
        )
        return ConversationHandler.END

    context.user_data.full_name = f'{update.effective_user.first_name} {update.effective_user.last_name}'

    if context.user_data.full_name == "":
        context.user_data.name = update.effective_user.name

    reply_keyboard = [
        [
            InlineKeyboardButton("Add Sonarr", callback_data="add_sonarr"),
            InlineKeyboardButton("Add Radarr", callback_data="add_radarr"),
            InlineKeyboardButton("Add Readarr", callback_data="add_readarr"),
        ],
        [
            InlineKeyboardButton("Self Debug", callback_data="print_config"),
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
    """
    The callback that occurs when a user clicks "Add Sonarr"
    :param update:
    :param context:
    :return:
    """
    query = update.callback_query
    await query.answer()

    await query.message.delete()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide a hostname for your server"
    )

    return ADD_SONARR_HOSTNAME


async def add_sonarr_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The callback that records the entered value for the sonarr hostname
    :param update:
    :param context:
    :return:
    """
    hostname = update.message.text
    context.user_data['tmp_sonarr_hostname'] = hostname
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide an API token for your server"
    )
    return ADD_SONARR_TOKEN


async def add_sonarr_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The final callback when adding a sonarr server. Saves the config + notifies user
    :param update:
    :param context:
    :return:
    """
    try:
        context.user_data.save_servarr('sonarr', context.user_data['tmp_sonarr_hostname'], update.message.text)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{ADD_SUCCESS}'
        )
    except Exception as ex:
        print("Something else went wrong")
        print(ex)
        traceback.print_exc()
    finally:
        del context.user_data['tmp_sonarr_hostname']
        return ConversationHandler.END


async def add_radarr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The callback that occurs when a user clicks "Add Radarr"
    :param update:
    :param context:
    :return:
    """
    query = update.callback_query
    await query.answer()
    await query.message.delete()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide a hostname for your Radarr server"
    )

    return ADD_RADARR_HOSTNAME


async def add_radarr_hostname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The callback that records the entered value for the radarr hostname
    :param update:
    :param context:
    :return:
    """
    hostname = update.message.text
    context.user_data['tmp_radarr_hostname'] = hostname
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide an API token for your radarr server"
    )
    return ADD_RADARR_TOKEN


async def add_radarr_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The final callback when adding a radarr server. Saves the config + notifies user
    :param update:
    :param context:
    :return:
    """
    try:
        context.user_data.save_servarr('radarr', context.user_data['tmp_radarr_hostname'], update.message.text)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{ADD_SUCCESS}'
        )
    except Exception as ex:
        print("Something else went wrong")
        print(ex)
    finally:
        del context.user_data['tmp_radarr_hostname']
        return ConversationHandler.END


async def add_readarr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The callback that occurs when a user clicks "Add Readarr"
    :param update:
    :param context:
    :return:
    """
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide a hostname for your Readarr server"
    )

    return ADD_READARR_HOSTNAME


async def add_readarr_hostname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The callback that records the entered value for the readarr hostname
    :param update:
    :param context:
    :return:
    """
    hostname = update.message.text
    context.user_data['tmp_readarr_hostname'] = hostname
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please provide an API token for your readarr server"
    )
    return ADD_READARR_TOKEN


async def add_readarr_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The final callback when adding a readarr server. Saves the config + notifies user
    :param update:
    :param context:
    :return:
    """
    try:
        context.user_data.save_servarr('readarr', context.user_data['tmp_readarr_hostname'], update.message.text)
        context.user_data['readarr'] = ReadarrApi(**context.user_data.get_readarr_settings())
        context.user_data['readarr'].configure_notifications(str(update.effective_chat.id), os.getenv('TOKEN'))
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{ADD_SUCCESS} {context.user_data.share()}'
        )
    except Exception as ex:
        print("Something else went wrong")
        print(ex)
    finally:
        del context.user_data['tmp_readarr_hostname']
        return ConversationHandler.END


async def start_share_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback made when a user clicks "Share Access"
    :param update:
    :param context:
    :return:
    """
    query = update.callback_query
    await query.answer()
    await query.message.delete()

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Please enter the share code you want to use"
    )
    return SHARE_ACCESS


async def share_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback called once a user has input a share code to share access from another user
    :param update:
    :param context:
    :return:
    """
    share_code = update.message.text
    context.application.persistence.lookup_user(share_code)
    context.user_data.receive_access(context.application.persistence.lookup_user(share_code))
    await update.message.reply_text(
        'Access granted. You can now use those servers to download shows,movies and books'
    )
    return ConversationHandler.END


async def print_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Method to output the current configuration of the user for debugging
    :param update:
    :param context:
    :return:
    """
    await update.callback_query.answer()
    user = context.user_data.get_config()
    await update.callback_query.delete_message()
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=user
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=context.user_data.debug()
    )
    return ConversationHandler.END


CONVERSATION = ConversationHandler(
    entry_points=[CommandHandler("config", entry_point)],
    states={
        START: [
            CallbackQueryHandler(add_sonarr, pattern="^add_sonarr"),
            CallbackQueryHandler(add_radarr, pattern="^add_radarr"),
            CallbackQueryHandler(add_readarr, pattern="^add_readarr"),
            CallbackQueryHandler(print_config, pattern="^print_config"),
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
        ADD_READARR_HOSTNAME: [
            MessageHandler(filters=filters.TEXT, callback=add_readarr_hostname)
        ],
        ADD_READARR_TOKEN: [
            MessageHandler(filters=filters.TEXT, callback=add_readarr_token)
        ],
        SHARE_ACCESS: [
            MessageHandler(filters=filters.TEXT, callback=share_access)
        ]
    },
    fallbacks=[CommandHandler("config", entry_point)]
)
