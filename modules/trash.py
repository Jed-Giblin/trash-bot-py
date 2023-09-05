from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, filters, MessageHandler
import re
from modules.utils import ModTypes
from modules.db import db as mydb

MOD_TYPE = ModTypes.COMMAND_DRIVEN


async def add_new_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            'This is only allowed in group chats'
        )
        return None
    if len(update.message.text.split('/newword ')) < 2:
        await update.message.reply_text(
            'Fuck you cole'
        )
        return None
    mydb.get_or_create_chat(str(update.effective_chat.id), update.effective_chat.effective_name)
    new_word = update.message.text.split('/newword ')[-1]
    if not len(new_word):
        await update.message.reply_text(
            'Empty words not allowed'
        )
        return None

    word = re.sub("[\.\*\[\]\(\)\?]", "", new_word)
    mydb.add_trash_word(update.effective_chat.id, word)
    await update.message.reply_text(
        'Added!'
    )
    return None


async def del_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            'This is only allowed in group chats'
        )
        return None

    mydb.get_or_create_chat(str(update.effective_chat.id), update.effective_chat.effective_name)
    new_word = update.message.text.split('/newword ')[-1]
    if not len(new_word):
        await update.message.reply_text(
            'Empty words not allowed'
        )
        return None
    word = re.sub("[\.\*\[\]\(\)\?]", "", new_word)
    mydb.remove_trash_word(update.effective_chat.id, word)
    await update.message.reply_text(
        'Removed!'
    )
    return None


async def handle_trash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_txt = update.message.text
    trash_words = mydb.get_trash_words(update.effective_chat.id)
    if not len(trash_words):
        return None

    for word in trash_words:
        regex = f'^.*{word}.*$'
        if re.match(regex, msg_txt, re.IGNORECASE):
            await update.message.reply_text(
                'Trash!'
            )
            return None
    return None


HANDLERS = [
    CommandHandler("newword", add_new_word),
    CommandHandler("delword", del_word),
    CommandHandler("memes", add_new_word),
    MessageHandler(filters=filters.ALL, callback=handle_trash, block=False)
]
