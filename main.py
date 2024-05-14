import asyncio
import html
import importlib
import json
import os
import traceback

import telegram.error
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest

from modules.db import EnhancedPicklePersistence
from telegram import Update
from telegram.ext import CommandHandler, ApplicationBuilder, PicklePersistence, ContextTypes, CallbackContext
from dotenv import load_dotenv
from telegram.warnings import PTBUserWarning
from modules.db_models import TGChat, TGUser
from modules.utils import ModTypes, TrashLogger, SUPPORT_CHAT_ID
from warnings import filterwarnings

logger = TrashLogger(name='Trash').logger
load_dotenv()
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    ticket_name = tb_list[-1].strip()
    if 'TOPICS' not in context.bot_data:
        context.bot_data['TOPICS'] = {}

    if ticket_name in context.bot_data.get('TOPICS').keys():
        topic_id = context.bot_data.get('TOPICS')[ticket_name]
        try:
            await context.bot.reopenForumTopic(chat_id=SUPPORT_CHAT_ID, message_thread_id=topic_id)
        except telegram.error.BadRequest:
            pass
    else:
        topic = await context.bot.createForumTopic(
            chat_id=SUPPORT_CHAT_ID,
            name=ticket_name,
        )
        context.bot_data['TOPICS'][ticket_name] = topic.message_thread_id
        topic_id = topic.message_thread_id

    # Finally, send the message
    await context.bot.send_message(
        chat_id=SUPPORT_CHAT_ID, text=message, parse_mode=ParseMode.HTML,
        message_thread_id=topic_id
    )


def main():
    # trash must always be last, because of the catchall
    modules = ['sonarr_manager', 'setup_manager', 'radarr_manager', 'readarr_manager', 'poll_manager', 'oncall_manager',
               'trash']
    context_types = ContextTypes(context=CallbackContext, chat_data=TGChat, user_data=TGUser, bot_data=dict)
    persistance = EnhancedPicklePersistence(filepath='./db/db.pickle')
    app = ApplicationBuilder().token(os.environ.get("TOKEN")).context_types(context_types).persistence(
        persistance).get_updates_http_version("1.1").http_version("1.1").build()
    app.add_error_handler(error_handler)
    for mod in modules:
        module = importlib.import_module(f'modules.{mod}')
        if module.MOD_TYPE == ModTypes.CONVERSATION:
            app.add_handler(module.CONVERSATION)

        elif module.MOD_TYPE == ModTypes.COMMAND_DRIVEN:
            app.add_handlers(module.HANDLERS)
            for m in module.HANDLERS:
                try:
                    logger.info(f'Adding support for command /{list(m.commands)[0]}')
                except AttributeError:
                    pass

        logger.info(f"Loaded Module: {mod}, Type: {module.MOD_TYPE}")
        try:
            app.job_queue.run_once(module.LOAD_FROM_DB, 5)
        except AttributeError:
            pass
    try:
        # Restart error handling on boot
        app.bot_data['TOPICS'] = {}
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as ex:
        traceback.print_exc()
        print(ex)
    finally:
        print("Final block")
        exit()


if __name__ == "__main__":
    main()
