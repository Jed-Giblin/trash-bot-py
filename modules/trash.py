from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, filters, MessageHandler
import re
from modules.utils import ModTypes, not_in_thread, not_in_support

MOD_TYPE = ModTypes.COMMAND_DRIVEN


@not_in_support
async def add_new_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            'This is only allowed in group chats'
        )
        return None
    new_word = update.message.text.split('/newword ')
    if len(new_word) == 1:
        await update.message.reply_text(
            'Empty words not allowed'
        )
        return None

    word = re.sub("[\.\*\[\]\(\)\?]", "", new_word[-1])
    context.chat_data.add_trash_word(word)
    await update.message.reply_text(
        'Added!'
    )
    return None


@not_in_support
async def del_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            'This is only allowed in group chats'
        )
        return None
    new_word = update.message.text.split('/delword ')
    if len(new_word) == 1:
        await update.message.reply_text(
            'Empty words not allowed'
        )
        return None
    word = re.sub("[\.\*\[\]\(\)\?]", "", new_word[-1])
    context.chat_data.remove_trash_word(word)
    await update.message.reply_text(
        'Removed!'
    )
    return None


@not_in_support
async def handle_trash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return None

    trash_words = context.chat_data.words
    if not len(trash_words):
        return None

    msg_txt = update.message.text if update.message.text else update.message.caption if update.message.caption else ''
    mid_regex = "[\s$]|[^\s]?".join(context.chat_data.words)
    regex = f'[^\s]?{mid_regex}[\s$]'
    if re.search(regex, msg_txt, re.IGNORECASE):
        res = await update.message.reply_text(
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
