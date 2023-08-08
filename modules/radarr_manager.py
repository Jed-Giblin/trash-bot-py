from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, Application, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters
from modules.db import db as mydb
from modules.radarr_api import RadarrApi
from modules.sonarr_api import SonarrApi
from modules.utils import ModTypes

MOD_TYPE = ModTypes.CONVERSATION
MAIN_MENU = 1
END = 2

COMMAND = 'movies'

NEW_MOVIE_SEARCH = 11
SELECT_SEARCH_RESULT = 21


async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "That's only allowed in private chats.", quote=True
        )
        return ConversationHandler.END
    reply_keyboard = [
        ["Add Movies"],
        ["Manage Movies"],
    ]

    reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "Please select an action", quote=True,
        reply_markup=reply_markup
    )
    return MAIN_MENU


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO - Empty context
    await update.callback_query.answer()
    await context.bot.send_message(
        text='Goodbye!', chat_id=update.effective_chat.id
    )
    return ConversationHandler.END


async def manage_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


async def add_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        reply_to_message_id=update.message.id, quote=True,
        text="Whats the movie name you want to add? Send me a message with its name. You can also press quit.",
        allow_sending_without_reply=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Quit", callback_data="quit")]])
    )

    return NEW_MOVIE_SEARCH


async def list_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_str = update.message.text
    radarr_config = get_and_validate_config(update.effective_user.id)
    context.user_data['radarr'] = RadarrApi(**radarr_config)
    context.user_data['movie_cache'] = {}

    btns = []
    for movie in context.user_data['radarr'].search_new_movies(search_str)[0:20]:
        import pprint
        pprint.pprint(movie)
        mv_id = movie['tmdbId']
        context.user_data['movie_cache'][mv_id] = movie
        slug = f'{movie["title"]} ({movie["year"]})'
        btns.append([InlineKeyboardButton(text=slug, callback_data=f"detail_{mv_id}")])

    await context.bot.send_message(
        text='Here are the top 20 results. You can also search again by sending me a new message',
        chat_id=update.effective_chat.id,
        reply_markup=InlineKeyboardMarkup(btns)
    )
    return SELECT_SEARCH_RESULT


async def detail_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    show_id = str(query.data.split('_')[-1])
    return -1


def get_and_validate_config(user_id):
    radarr_config = mydb.get_user(user_id)
    if not radarr_config:
        raise ValueError
    return radarr_config


CONVERSATION = ConversationHandler(
    entry_points=[CommandHandler(COMMAND, entry_point)],
    states={
        MAIN_MENU: [
            MessageHandler(filters.Regex("^Add Movies$"), callback=add_movies),
            MessageHandler(filters.Regex("^Manage Movies$"), callback=manage_movies),
        ],
        NEW_MOVIE_SEARCH: [
            MessageHandler(filters=filters.TEXT, callback=list_search_results),
            CallbackQueryHandler(stop, pattern="^quit$")
        ],
        SELECT_SEARCH_RESULT: [
            CallbackQueryHandler(stop, pattern="^quit$"),
            CallbackQueryHandler(detail_movie, pattern='^detail_[0-9]+$'),
            MessageHandler(filters=filters.TEXT, callback=list_search_results)
        ]
    },
    fallbacks=[CommandHandler("shows", entry_point)]
)
