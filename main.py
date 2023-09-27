import asyncio
import importlib
import os
import traceback
from modules.db import EnhancedPicklePersistence
from telegram import Update
from telegram.ext import CommandHandler, ApplicationBuilder, PicklePersistence, ContextTypes, CallbackContext
from dotenv import load_dotenv
from telegram.warnings import PTBUserWarning
from modules.db_models import TGChat, TGUser
from modules.utils import ModTypes, TrashLogger
from warnings import filterwarnings
logger = TrashLogger(name='Trash').logger
load_dotenv()
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

def main():
    modules = ['sonarr_manager', 'setup_manager', 'radarr_manager', 'readarr_manager', 'poll_manager', 'trash']
    context_types = ContextTypes(context=CallbackContext, chat_data=TGChat, user_data=TGUser)
    persistance = EnhancedPicklePersistence(filepath='./db/db.pickle')
    app = ApplicationBuilder().token(os.environ.get("TOKEN")).context_types(context_types).persistence(
        persistance).build()
    for mod in modules:
        module = importlib.import_module(f'modules.{mod}')
        if module.MOD_TYPE == ModTypes.CONVERSATION:
            app.add_handler(module.CONVERSATION)

        elif module.MOD_TYPE == ModTypes.COMMAND_DRIVEN:
            app.add_handlers(module.HANDLERS)

        try:
            app.job_queue.run_once(module.LOAD_FROM_DB, 5)
        except AttributeError:
            pass
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as ex:
        traceback.print_exc()
        print(ex)
    finally:
        print("Final block")
        exit()


if __name__ == "__main__":
    main()
