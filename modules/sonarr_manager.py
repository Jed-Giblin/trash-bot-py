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

CLEAN_SHOW_SEARCH = 21
CHOOSE_SHOW_TO_MANAGE = 22
MANAGE_SHOW = 23


async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        [InlineKeyboardButton("Add Shows", callback_data="add_shows")],
        [InlineKeyboardButton("Manage Shows", callback_data="list_user_shows")],
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


async def search_sonarr_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_str = update.message.text
    try:
        sonarr_config = await get_and_validate_config(update.message.from_user.id)
    except ValueError:
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
    success, msg, res = context.user_data['sonarr'].add_show(show, update.effective_user.id)
    if success:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Successfully added shows. Trying to search for the latest season now')
        context.user_data['sonarr'].search_for_episodes(res.get("id"))
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Episode searching is underway')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"The show couldn't be added: {msg}")

    del context.user_data['sonarr']
    return ConversationHandler.END


async def list_user_shows(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.delete()

    try:
        sonarr_config = await get_and_validate_config(update.effective_user.id)
    except ValueError:
        await context.bot.send_message(
            chat_id=update.message.from_user.id,
            text="You have not configured a server.Exiting."
        )
        return ConversationHandler.END

    context.user_data['sonarr'] = SonarrApi(**sonarr_config)

    btns = [InlineKeyboardButton(text=s['title'], callback_data=f'manage_{s["id"]}') for s in
            context.user_data['sonarr'].search_existing_shows_by_tag(f'tg:{update.effective_user.id}')]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please choose a show to manage",
        reply_markup=InlineKeyboardMarkup([[btn] for btn in btns])
    )

    return CHOOSE_SHOW_TO_MANAGE


async def manage_show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    show_id = update.callback_query.data.split('_')[-1]
    await query.message.delete()

    show = context.user_data['sonarr'].get_show(show_id)
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=show.get("images")[0].get("remoteUrl")
    )
    await context.bot.send_message(
        text='What would you like to do?',
        chat_id=update.effective_chat.id,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(text='Delete Show', callback_data=f'delete_{show_id}')],
                [InlineKeyboardButton(text='Download More Seasons', callback_data=f'man_season_{show_id}')]
            ]
        )
    )
    return MANAGE_SHOW


async def delete_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    show_id = update.callback_query.data.split('_')[-1]
    await query.message.delete()
    res = context.user_data['sonarr'].delete_show(show_id)
    if res:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Show Deleted'
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Failed to delete show'
        )
    del context.user_data['sonarr']
    return ConversationHandler.END


async def manage_show_seaons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    show_id = update.callback_query.data.split('_')[-1]
    await query.message.delete()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Apologies. This feature is not yet implemented'
    )
    return ConversationHandler.END


async def get_and_validate_config(user_id):
    sonarr_config = mydb.get_user(user_id)
    if not sonarr_config:
        raise ValueError
    return sonarr_config


CONVERSATION = ConversationHandler(
    entry_points=[CommandHandler("shows", entry_point)],
    states={
        START: [
            CallbackQueryHandler(add_shows, pattern="^add_shows$"),
            CallbackQueryHandler(list_user_shows, pattern="^list_user_shows"),
        ],
        NEW_SHOW_SEARCH: [
            MessageHandler(filters=filters.TEXT, callback=search_sonarr_new)
        ],
        SHOW_PICKER: [
            CallbackQueryHandler(show_clicked, pattern="^add_show_[0-9]+$")
        ],
        CONFIRM_SHOW: [
            CallbackQueryHandler(confirm_show_add, pattern="^confirm_[0-9]+$"),
            CallbackQueryHandler(show_clicked, pattern="^add_show_[0-9]+$")
        ],
        CHOOSE_SHOW_TO_MANAGE: [
            CallbackQueryHandler(manage_show_menu, pattern="^manage_[0-9]+$"),
        ],
        MANAGE_SHOW: [
            CallbackQueryHandler(delete_show, pattern="^delete_[0-9]+$"),
            CallbackQueryHandler(manage_show_seaons, pattern="^man_season_[0-9]+$")
        ]
    },
    fallbacks=[CommandHandler("shows", entry_point)]
)
