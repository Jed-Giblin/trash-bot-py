import logging

import telegram
from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

SEASON_UPDATE = {"monitored": False}
premium_chat_whitelist = [int(-1001401984428)]
STOP_BUTTON = [InlineKeyboardButton(text='Quit (Stop talking to me Trashbot)', callback_data=f'quit')]
SUPPORT_CHAT_ID = -1001966556022


def manipulate_seasons(seasons, show_type):
    sorted_seasons = sorted(seasons, key=lambda s: s.get("seasonNumber"))
    edited_seasons = [{**season, **SEASON_UPDATE} for season in sorted_seasons]
    # Shows that are over, we instead want the first season
    mon_index = -1 if show_type != "ended" else 1
    try:
        # Somtimes, shows don't list the season0 for some reason
        edited_seasons[mon_index]['monitored'] = True
    except IndexError:
        edited_seasons[mon_index - 1]['monitored'] = True
    return edited_seasons


def manage_seasons(seasons):
    pass


class ModTypes:
    CONVERSATION = 1
    COMMAND_DRIVEN = 2


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(asctime)s][%(process)s][%(levelname)s][%(filename)s:%(lineno)s]: %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        """Sets the logging formatter details"""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class TrashLogger(object):
    """Singleton logging class to be used to keep logging levels and color across any script/lib"""

    def __init__(self, name='Trash', level=logging.INFO):
        """
        Generates a logger object that will be used across all scripts/libs that utilize this logging class

        :param name: The name to define this logger
        :param level: The logging level to use. Examples: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
        """
        self.logger = self.generate_logger(name, level=level)

    def generate_logger(self, name, level=logging.INFO):
        """Generates the logging handler

        :param name: The name to define this logger
        :param level: The logging level to use. Examples: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
        :return: :class:`Logger <Logger>` object
        """
        log = logging.getLogger(name)
        log.setLevel(level)
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(CustomFormatter())
        log.addHandler(log_handler)
        return log


def premium_only(wrapped_method):
    """
    This decorator will lookup if the user is in a "premium" chat and silently exit if not
    :param wrapped_method:
    :return:
    """

    async def wrapper(*args, **kwargs):
        update, context = args
        wl = False
        print("Checking premium status")
        for chat_id in premium_chat_whitelist:
            print(f"Are they in {chat_id}")
            try:
                await context.bot.get_chat_member(chat_id, context.user_data.id)
                wl = True
            except telegram.error.BadRequest:
                pass
        if not wl:
            print("User not in WL")
            return None
        return await wrapped_method(*args, **kwargs)

    return wrapper


def chat_only(wrapped_method):
    """
        This decortor will force the handler to only allow the command to execute in a group chat only
        :param wrapped_method:
        :return:
        """

    async def wrapper(*args, **kwargs):
        update, context = args
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "That's only allowed in group chats.", quote=True
            )
            return ConversationHandler.END
        return await wrapped_method(*args, **kwargs)

    return wrapper


def dm_only(wrapped_method):
    """
    This decortor will force the handler to only allow the command to execute in a DM and notify the user of such
    :param wrapped_method:
    :return:
    """

    async def wrapper(*args, **kwargs):
        update, context = args
        if update.effective_chat.type != "private":
            await update.message.reply_text(
                "That's only allowed in private chats.", quote=True
            )
            return ConversationHandler.END
        return await wrapped_method(*args, **kwargs)

    return wrapper


def not_in_thread(wrapped_method):
    async def wrapper(*args: [Update, ContextTypes.DEFAULT_TYPE], **kwargs):
        update, context = args
        if update.message.is_topic_message:
            return ConversationHandler.END
        return await wrapped_method(*args, **kwargs)

    return wrapper


def not_in_support(wrapped_method):
    async def wrapper(*args: [Update, ContextTypes.DEFAULT_TYPE], **kwargs):
        update, context = args
        if update.effective_chat.id == SUPPORT_CHAT_ID:
            return ConversationHandler.END
        return await wrapped_method(*args, **kwargs)

    return wrapper


def update_user(wrapped_method):
    """
    This decorator will store user attributes on context data
    :param wrapped_method:
    :return:
    """

    async def wrapper(*args, **kwargs):
        update, context = args
        context.user_data.full_name = f'{update.effective_user.first_name} {update.effective_user.last_name}'
        context.user_data.id = update.effective_user.id
        return await wrapped_method(*args, **kwargs)

    return wrapper
