from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters
from modules.db import db as mydb
from modules.sonarr_api import SonarrApi

COMMAND = 'shows'
START = 1
END = 2

NEW_SHOW_SEARCH = 11
SHOW_PICKER = 12
CONFIRM_SHOW = 13


async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        [
            InlineKeyboardButton("Add Shows", callback_data="add_shows"),
            InlineKeyboardButton("Delete Shows", callback_data="rm_shows"),
            InlineKeyboardButton("List Shows", callback_data="ls_shows")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(reply_keyboard)
    await update.message.reply_text(
        "Please select an action",
        reply_markup=reply_markup
    )
    return START


async def add_shows(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.delete()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Whats the show name you want to add?"
    )

    return NEW_SHOW_SEARCH


async def search_sonarr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_str = update.message.text
    sonarr_config = mydb.get_user(update.message.from_user.id)
    if not sonarr_config:
        await context.bot.send_message(
            chat_id=update.message.from_user.id,
            text="You have not configured a server.Exiting."
        )
        return ConversationHandler.END
    context.user_data['sonarr'] = SonarrApi(**sonarr_config)
    context.user_data['show_cache'] = {}
    buttons = []
    for show in context.user_data['sonarr'].search(query_str)[0:20]:
        show_id = str(show['tvdbId'])
        context.user_data['show_cache'][show_id] = show
        buttons.append(InlineKeyboardButton(show["title"], callback_data=f"add_show_{show_id}"))

    markup = [[btn] for btn in buttons]
    await context.bot.send_message(text='Here are the top 20 results',
                                   chat_id=update.message.chat_id,
                                   reply_markup=InlineKeyboardMarkup(markup))

    return SHOW_PICKER


async def show_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    show_id = str(query.data.split('_')[-1])
    show = context.user_data['show_cache'].get(show_id)
    if show.get("remotePoster"):
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=show.get("remotePoster"))
    show_str = f'{show.get("title")} ({show.get("year")}) ({show.get("network")}'
    btns = [InlineKeyboardButton("Click here to add", callback_data=f"confirm_{show_id}")]
    await context.bot.send_message(
        text=show_str,
        chat_id=update.effective_chat.id,
        reply_markup=InlineKeyboardMarkup([btns])
    )
    return CONFIRM_SHOW


async def confirm_show_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    show_id = str(query.data.split('_')[-1])
    show = context.user_data['show_cache'].get(show_id)
    del context.user_data['show_cache']
    await context.bot.send_message(text='Adding Show!', chat_id=update.effective_chat.id)
    success, msg = context.user_data['sonarr'].add_show(show, update.effective_user.id)
    if success:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Successfully added shows. Trying to search for the latest season now')
        # context.user_data['sonarr'].search_for_episodes()
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"The show couldn't be added: {msg}")

    return ConversationHandler.END


async def rm_shows(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


async def ls_shows(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


CONVERSATION = ConversationHandler(
    entry_points=[CommandHandler("shows", entry_point)],
    states={
        START: [
            CallbackQueryHandler(add_shows, pattern="^add_shows$"),
            CallbackQueryHandler(rm_shows, pattern="^rm_shows$"),
            CallbackQueryHandler(ls_shows, pattern="^ls_shows$"),
        ],
        NEW_SHOW_SEARCH: [
            MessageHandler(filters=filters.TEXT, callback=search_sonarr)
        ],
        SHOW_PICKER: [
            CallbackQueryHandler(show_clicked, pattern="^add_show_[0-9]+$")
        ],
        CONFIRM_SHOW: [
            CallbackQueryHandler(confirm_show_add, pattern="^confirm_[0-9]+$"),
            CallbackQueryHandler(show_clicked, pattern="^add_show_[0-9]+$")
        ]
    },
    fallbacks=[CommandHandler("shows", entry_point)]
)
