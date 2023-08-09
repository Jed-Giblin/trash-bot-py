from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, Application, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters
from modules.db import db as mydb
from modules.radarr_api import RadarrApi
from modules.sonarr_api import SonarrApi
from modules.utils import ModTypes
import requests
import os

MOD_TYPE = ModTypes.CONVERSATION
MAIN_MENU = 1
END = 2

COMMAND = 'movies'

NEW_MOVIE_SEARCH = 11
SELECT_SEARCH_RESULT = 21
CONFIRM_MOVIE_OR_SELECT_NEW = 22


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
    await context.bot.send_message(
        text='Sorry, I haven"t set this up yet', chat_id=update.effective_chat.id
    )
    return ConversationHandler.END


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
    context.user_data['downloads'] = []

    btns = []
    for movie in sorted(context.user_data['radarr'].search_new_movies(search_str), key=(lambda x: x["popularity"]))[
                 0:20]:
        mv_id = str(movie['tmdbId'])
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
    movie_id = str(query.data.split('_')[-1])

    movie = context.user_data['movie_cache'][movie_id]
    if movie.get("images"):
        poster_url = movie.get("images")[0].get("remoteUrl")
        context.user_data['downloads'].append(write_file(f'./tmp/movies', f'{movie_id}.jpg', poster_url))
        with open(f'./tmp/movies/{movie_id}.jpg', 'rb') as f:
            await context.bot.send_photo(update.effective_chat.id, photo=f)
    show_str = f'{movie.get("title")} ({movie.get("year")})'
    btns = [InlineKeyboardButton("Click here to add", callback_data=f"confirm_{movie_id}")]
    await context.bot.send_message(
        text=show_str,
        chat_id=update.effective_chat.id,
        reply_markup=InlineKeyboardMarkup([btns])
    )
    return CONFIRM_MOVIE_OR_SELECT_NEW


async def confirm_movie_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = str(query.data.split('_')[-1])
    movie = context.user_data['movie_cache'][movie_id]
    success, msg = context.user_data['radarr'].add_movie(movie, str(update.effective_chat.id))
    if success:
        await context.bot.send_message(
            text='Movie added', chat_id=update.effective_chat.id
        )
    else:
        await context.bot.send_message(
            text='Unable to add movie', chat_id=update.effective_chat.id
        )
    return ConversationHandler.END


def get_and_validate_config(user_id):
    radarr_config = mydb.get_user(user_id)
    if not radarr_config:
        raise ValueError
    return radarr_config


def write_file(path, filename, remote):
    if not os.path.exists(path):
        os.makedirs(path)
    r = requests.get(remote)
    if r.status_code == 200:
        with open(f'{path}/{filename}', 'wb') as f:
            for chunk in r:
                f.write(chunk)
    return f'{path}/{filename}'


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
        ],
        CONFIRM_MOVIE_OR_SELECT_NEW: [
            CallbackQueryHandler(stop, pattern="^quit$"),
            CallbackQueryHandler(confirm_movie_add, pattern="^confirm_[0-9]+$"),
            CallbackQueryHandler(detail_movie, pattern='^detail_[0-9]+$')
        ]
    },
    fallbacks=[CommandHandler("shows", entry_point)]
)
