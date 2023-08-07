import asyncio
import importlib
import os
from modules.db import db
from telegram import Update
from telegram.ext import CommandHandler, ApplicationBuilder
from dotenv import load_dotenv

load_dotenv()


def main():
    modules = ['sonarr_manager', 'setup_manager']
    app = ApplicationBuilder().token(os.environ.get("TOKEN")).build()
    for mod in modules:
        module = importlib.import_module(f'modules.{mod}')
        app.add_handler(module.CONVERSATION)

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
