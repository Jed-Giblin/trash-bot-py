import telegram
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, Application, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters
from modules.radarr_api import RadarrApi
from modules.utils import ModTypes, dm_only, update_user, STOP_BUTTON
import requests
import os

MOD_TYPE = ModTypes.CONVERSATION
MAIN_MENU = 1
END = 2

COMMAND = 'movies'

NEW_MOVIE_SEARCH = 11
SELECT_SEARCH_RESULT = 21
CONFIRM_MOVIE_OR_SELECT_NEW = 22


@dm_only
@update_user
async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the command /movies
    :param update:
    :param context:
    :return:
    """
    reply_keyboard = [
        [InlineKeyboardButton("Add Movies", callback_data="add_movie")],
        [InlineKeyboardButton("Manage Movies", callback_data="manage_movies")],
    ]

    reply_markup = InlineKeyboardMarkup(reply_keyboard)
    await update.message.reply_text(
        "Please select an action", quote=True,
        reply_markup=reply_markup
    )
    return MAIN_MENU


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Called whenever a user clicks cancel
    :param update:
    :param context:
    :return:
    """
    await clear_cache(context.user_data, context)
    await update.callback_query.answer()
    await update.callback_query.message.edit_text('Goodbye', reply_markup=None)
    return ConversationHandler.END


async def manage_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        text='Sorry, I haven"t set this up yet', chat_id=update.effective_chat.id
    )
    return ConversationHandler.END


async def add_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for responding to "Add Movies" callback
    :param update:
    :param context:
    :return:
    """
    qb = update.callback_query
    await qb.answer()
    context.user_data['del_msg_id'] = update.callback_query.message.id

    await qb.message.edit_text(
        text="Whats the movie name you want to add? Send me a message with its name. You can also press quit.",
        reply_markup=InlineKeyboardMarkup([STOP_BUTTON])
    )

    return NEW_MOVIE_SEARCH


async def list_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback handler executed when a search query is presented
    :param update:
    :param context:
    :return:
    """
    search_str = update.message.text
    radarr_config = context.user_data.get_radarr_settings()
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

    btns.append(STOP_BUTTON)
    await context.bot.send_message(
        text='Here are the top 20 results. You can also search again by sending me a new message',
        chat_id=update.effective_chat.id,
        reply_markup=InlineKeyboardMarkup(btns)
    )
    return SELECT_SEARCH_RESULT


async def detail_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback handler when a movie is selected from a list of search results
    :param update:
    :param context:
    :return:
    """
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
    m = await context.bot.send_message(
        text=show_str,
        chat_id=update.effective_chat.id,
        reply_markup=InlineKeyboardMarkup([btns])
    )
    context.user_data.del_msg_list.append(m.id)
    msg = """
    If this wasn't the movie you wanted,you can: \n1. Click another from the list above\n2.Search again by typing in a name
3. Quit by clicking quit above"
    """
    m = await context.bot.send_message(
        text=msg, chat_id=update.effective_user.id)
    context.user_data.del_msg_list.append(m.id)
    return CONFIRM_MOVIE_OR_SELECT_NEW


async def confirm_movie_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_id = str(query.data.split('_')[-1])
    movie = context.user_data['movie_cache'][movie_id]
    try:
        context.user_data['radarr'].add_movie(movie, str(update.effective_chat.id))
        await context.bot.send_message(
            text='Movie added', chat_id=update.effective_chat.id
        )
    except ValueError as ex:
        await context.bot.send_message(
            text=f'Unable to add movie. {ex}', chat_id=update.effective_chat.id
        )
    await clear_cache(context.user_data, context)
    return ConversationHandler.END


def write_file(path, filename, remote):
    """
    Store a local copy of the poster to send. Works better with TG caching then sending a remoteURL
    :param path:
    :param filename:
    :param remote:
    :return:
    """
    if not os.path.exists(path):
        os.makedirs(path)
    r = requests.get(remote)
    if r.status_code == 200:
        with open(f'{path}/{filename}', 'wb') as f:
            for chunk in r:
                f.write(chunk)
    return f'{path}/{filename}'


async def clear_cache(cache, context):
    """
    Helper function to clear out stored tmp data during user interaction
    :param cache:
    :return:
    """
    cache['movie_cache'] = {}
    cache['downloads'] = []
    if context.user_data.del_msg_list and len(context.user_data.del_msg_list):
        for msg_id in context.user_data.del_msg_list:
            try:
                await context.bot.delete_message(chat_id=context.user_data.id, message_id=msg_id)
            except telegram.error.BadRequest as ex:
                pass
            context.user_data.del_msg_list.remove(msg_id)


CONVERSATION = ConversationHandler(
    entry_points=[CommandHandler(COMMAND, entry_point)],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(add_movies, pattern="^add_movie$"),
            CallbackQueryHandler(manage_movies, pattern="^manage_movies$"),
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
            CallbackQueryHandler(detail_movie, pattern='^detail_[0-9]+$'),
            MessageHandler(filters=filters.TEXT, callback=list_search_results)
        ]
    },
    fallbacks=[CommandHandler("movies", entry_point)]
)
