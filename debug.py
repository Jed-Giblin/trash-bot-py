import os
import pprint

from dotenv import load_dotenv
from telegram.ext import ContextTypes, CallbackContext, ApplicationBuilder

from modules.db import EnhancedPicklePersistence
from modules.db_models import TGChat, TGUser
import asyncio

load_dotenv()


async def main():
    context_types = ContextTypes(context=CallbackContext, chat_data=TGChat, user_data=TGUser)
    persistance = EnhancedPicklePersistence(filepath='./db/db.pickle')
    app = ApplicationBuilder().token(os.environ.get("TOKEN")).context_types(context_types).persistence(
        persistance).build()
    d = await app.persistence.get_user_data()
    for id, user in d.items():
        pprint.pprint(user.__dict__)

    c = await app.persistence.get_chat_data()
    for id, chat in c.items():
        pprint.pprint(chat.__dict__)
    b = await app.persistence.get_bot_data()
    print(b)


if __name__ == "__main__":
    asyncio.run(main())
