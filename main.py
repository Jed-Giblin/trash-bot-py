import asyncio
import importlib
import os
from modules.db import db
from telegram import Update
from telegram.ext import CommandHandler, ApplicationBuilder
from dotenv import load_dotenv

from modules.utils import ModTypes

load_dotenv()


def main():
    modules = ['sonarr_manager', 'setup_manager', 'trash', 'radarr_manager']
    app = ApplicationBuilder().token(os.environ.get("TOKEN")).build()
    for mod in modules:
        module = importlib.import_module(f'modules.{mod}')
        if module.MOD_TYPE == ModTypes.CONVERSATION:
            app.add_handler(module.CONVERSATION)

        elif module.MOD_TYPE == ModTypes.COMMAND_DRIVEN:
            app.add_handlers(module.HANDLERS)

    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as ex:
        print(ex)
    finally:
        print("Final block")
        db.handle_exit()
        exit()


if __name__ == "__main__":
    main()
