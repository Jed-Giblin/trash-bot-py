from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from modules.utils import ModTypes

MOD_TYPE = ModTypes.COMMAND_DRIVEN


async def add_new_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='You tried to add a word to trash, but this isnt implemented yet'
    )


HANDLERS = [
    CommandHandler("newword", add_new_word),
    CommandHandler("delword", add_new_word),
    CommandHandler("memes", add_new_word)
]