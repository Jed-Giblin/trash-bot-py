import datetime

import telegram.error
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters
# from modules.sonarr_api import SonarrApi
from pyarr import SonarrAPI
from modules.utils import ModTypes, manage_seasons

MOD_TYPE = ModTypes.CONVERSATION
import time

COMMAND = 'shows'
START = 1
END = 2

NEW_SHOW_SEARCH = 11
SHOW_PICKER = 12
CONFIRM_SHOW = 13
TRACK_PROGRESS = 14

CLEAN_SHOW_SEARCH = 21
CHOOSE_SHOW_TO_MANAGE = 22
MANAGE_SHOW = 23
MANAGE_SHOW_SEASON = 24


def ordinal(n: int):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix


async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "That's only allowed in private chats.", quote=True
        )
        return ConversationHandler.END

    if context.user_data.name == "":
        context.user_data.name = update.effective_user.name

    reply_keyboard = [
        [InlineKeyboardButton("Add Shows", callback_data="add_shows")],
        [InlineKeyboardButton("Manage Shows", callback_data="list_user_shows")],
    ]
    reply_markup = InlineKeyboardMarkup(reply_keyboard)
    await update.message.reply_text(
        "Please select an action", quote=True,
        reply_markup=reply_markup
    )
    return START


async def add_shows(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['del_msg_id'] = update.callback_query.message.id
    await update.callback_query.message.edit_text(
        text="Whats the show name you want to add?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Quit", callback_data="quit")]])
    )

    return NEW_SHOW_SEARCH


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO - Empty context
    await check_and_clear_messages(context, update.effective_chat.id)
    if 'sonarr' in context.user_data:
        del context.user_data['sonarr']
    await update.callback_query.answer()
    await update.callback_query.message.edit_text('Goodbye', reply_markup=None)
    return ConversationHandler.END


async def search_sonarr_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_str = update.message.text
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data['del_msg_id'])
    loader = await context.bot.send_animation(chat_id=update.effective_chat.id, animation='./loading.gif')
    try:
        context.user_data['sonarr'] = SonarrAPI(**context.user_data.get_sonarr_settings())
    except ValueError:
        await context.bot.send_message(
            chat_id=update.message.from_user.id,
            text="You have not configured a server.Exiting."
        )
        return ConversationHandler.END

    context.user_data['show_cache'] = {}
    buttons = []
    for show in context.user_data['sonarr'].lookup_series(query_str)[0:20]:
        show_id = str(show['tvdbId'])
        context.user_data['show_cache'][show_id] = show
        buttons.append(InlineKeyboardButton(show["title"], callback_data=f"add_show_{show_id}"))

    markup = [[btn] for btn in buttons]
    context.user_data['search_results'] = markup
    await loader.delete()
    return await show_search_results(update, context)


async def show_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data['search_results']:
        raise Exception("How did this happen?")
    await update.message.reply_text(
        quote=True,
        text='Here are the top 20 results. You can click any of these.',
        reply_markup=InlineKeyboardMarkup(context.user_data['search_results']))
    return SHOW_PICKER


async def check_and_clear_messages(context: ContextTypes.DEFAULT_TYPE, chat_id):
    if context.user_data.del_msg_list and len(context.user_data.del_msg_list):
        for msg_id in context.user_data.del_msg_list:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except telegram.error.BadRequest as ex:
                pass
            context.user_data.del_msg_list.remove(msg_id)


async def show_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await check_and_clear_messages(context, update.effective_chat.id)
    show_id = str(query.data.split('_')[-1])
    show = context.user_data['show_cache'].get(show_id)
    if show.get("remotePoster"):
        poster = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=show.get("remotePoster"))
        context.user_data.del_msg_list.append(poster.id)
    show_str = f'{show.get("title")} ({show.get("year")}) ({show.get("network")})'
    btns = [InlineKeyboardButton("Click here to add", callback_data=f"confirm_{show_id}")]
    msg = await context.bot.send_message(
        text=show_str,
        chat_id=update.effective_chat.id,
        reply_markup=InlineKeyboardMarkup([btns])
    )
    context.user_data.del_msg_list.append(msg.id)
    return CONFIRM_SHOW


async def confirm_show_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await check_and_clear_messages(context, update.effective_chat.id)
    show_id = str(query.data.split('_')[-1])
    show = context.user_data['show_cache'].get(show_id)
    del context.user_data['show_cache']
    await context.bot.send_message(text='Adding Show!', chat_id=update.effective_chat.id)
    res = context.user_data['sonarr'].add_series(
        setup_show(show, f'tg:{update.effective_user.id}', context.user_data['sonarr']), quality_profile_id=1,
        monitored=True, root_dir='/tv', language_profile_id=1)
    if res:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Successfully added shows. Trying to search for the latest season now')
        context.user_data['sonarr'].post_command(name='SeriesSearch', seriesId=res.get("id"))
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Episode searching is underway')
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Are you interested in tracking this process?',
                                       reply_markup=InlineKeyboardMarkup([
                                           [InlineKeyboardButton("Yes!",
                                                                 callback_data=f"track_progress_{res.get('id')}")],
                                           [InlineKeyboardButton("No! Its done when its done", callback_data="quit")]
                                       ]))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"The show couldn't be added. Ask Jed or Cole")
    return TRACK_PROGRESS


async def track_add_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    show_id = str(query.data.split('_')[-1])
    loader = await context.bot.send_animation(chat_id=update.effective_chat.id, animation='./loading.gif')
    context.job_queue.run_once(
        callback=track_show_add_progress,
        when=5.0,
        chat_id=update.effective_chat.id,
        user_id=update.effective_chat.id,
        name=f'track_show_add_progress_{show_id}',
        data={
            'queue_only': False,
            'show_id': show_id,
            'load_id': loader.id,
            'chat_id': update.effective_chat.id
        }
    )


async def track_show_add_progress(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    show_id = job.data.get("show_id")
    try:
        series = context.user_data['sonarr'].get_series(id_=show_id)
        check_queue = await output_progress(context, series)
        if check_queue or job.data.get("queue_only"):
            await context.bot.send_message(chat_id=job.data.get("chat_id"),
                                           text="I'll need some more time to give you more details.")
            loader = await context.bot.send_animation(chat_id=job.data.get("chat_id"), animation='./loading.gif')
            context.job_queue.run_once(
                callback=track_queue,
                when=30.0,
                chat_id=job.data.get("chat_id"),
                user_id=job.data.get("chat_id"),
                name=f'track_show_add_progress_{show_id}',
                data={
                    'queue_only': True,
                    'show_id': show_id,
                    'load_id': loader.id,
                    'chat_id': job.data.get("chat_id")
                }
            )

    except telegram.error.BadRequest:
        pass


async def track_queue(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    show_id = job.data.get("show_id")
    chat_id = job.data.get("chat_id")
    episodes_before = 0
    queue_depth = 0
    first_index = 1
    show_found = False
    sonarr = context.user_data['sonarr']
    for episode in sonarr.get_queue(include_episode=True).get("records"):
        if not show_found and not episode['seriesId'] == show_id:
            episodes_before += 1
        if episode['seriesId'] == show_id:
            show_found = True
            first_index = queue_depth
        queue_depth += 1
    message = f'There are {queue_depth} things in the queue, and your show is {ordinal(first_index)} in line'
    await context.bot.delete_message(chat_id=chat_id, message_id=job.data.get("load_id"))
    await context.bot.send_message(chat_id=chat_id, text=message)


async def output_progress(context: ContextTypes.DEFAULT_TYPE, series):
    monitored_count = 0
    messages = []
    check_queue = False
    job = context.job
    ignored_seasons = []
    ignored_msg = 'Seasons {}'
    for season in series.get("seasons"):
        if season['monitored']:
            monitored_count += 1
            messages.append(
                f'Season {season["seasonNumber"]} is {season["statistics"]["percentOfEpisodes"]}% downloaded')
            if int(season["statistics"]["percentOfEpisodes"]) != 100:
                check_queue = True
        else:
            ignored_seasons.append(str(season["seasonNumber"]))
    messages.append(ignored_msg.format(f"{','.join(ignored_seasons)} are not being monitored and wont be available"))
    await context.bot.delete_message(chat_id=job.data.get("chat_id"), message_id=job.data.get("load_id"))
    for message in messages:
        await context.bot.send_message(chat_id=job.data.get("chat_id"),
                                       text=message)
    return check_queue


async def list_user_shows(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        context.user_data['sonarr'] = SonarrAPI(**context.user_data.get_sonarr_settings())
    except ValueError:
        await context.bot.send_message(
            chat_id=update.message.from_user.id,
            text="You have not configured a server.Exiting."
        )
        return ConversationHandler.END
    tag = next(filter(lambda x: x.get("label") == f'tg:{update.effective_user.id}',
                      context.user_data['sonarr'].get_tag_detail()), None)
    btns = []
    for series_id in tag.get("seriesIds"):
        show = context.user_data['sonarr'].get_series(id_=series_id)
        btns.append(
            InlineKeyboardButton(text=show['title'], callback_data=f'manage_{show["id"]}')
        )
    btns.append(InlineKeyboardButton(text="Quit! (not a show)", callback_data=f'quit'))
    await update.callback_query.message.edit_text(
        text="Please choose a show to manage",
        reply_markup=InlineKeyboardMarkup([[btn] for btn in btns])
    )

    return CHOOSE_SHOW_TO_MANAGE


async def manage_show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    show_id = update.callback_query.data.split('_')[-1]
    await query.message.delete()

    show = context.user_data['sonarr'].get_series(id_=show_id)
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
    show = context.user_data['sonarr'].get_show(show_id)
    btns = [[InlineKeyboardButton("Quit", callback_data="quit")]]
    for season in sorted(show.get("seasons"), key=(lambda x: x.get("seasonNumber"))):
        slug = f"Season {season.get('seasonNumber')}"
        stats = season.get("statistics")
        # If the season isn't monitored OR only partially monitored, display that
        if season.get("monitored") or season.get("statistics").get("episodeCount") == season.get("statistics").get(
                "totalEpisodeCount"):
            continue
        slug = f'{slug} ({stats.get("episodeCount")} wanted of {stats.get("totalEpisodeCount")})'
        btns.append(
            [InlineKeyboardButton(text=slug,
                                  callback_data=f'show_{show_id}_s_{show.get("seasonNumber")}')])
    await context.bot.send_message(
        text='Please select a season to add or quit',
        reply_markup=InlineKeyboardMarkup(btns),
        chat_id=update.effective_chat.id
    )
    return MANAGE_SHOW_SEASON


async def add_show_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    show_id = update.callback_query.data.split('_')[1]
    await query.message.delete()
    return ConversationHandler.END


def setup_show(show, tag_value, sonarr):
    seasons = manage_seasons(show.get("seasons"))
    tag = next(filter(lambda x: x.get("label") == tag_value,
                      sonarr.get_tag()), None)

    if not tag:
        tag = sonarr.create_tag(label=tag_value)

    mod_show = {**show, 'seasons': seasons, 'tags': [tag.get("id")]}
    return mod_show


CONVERSATION = ConversationHandler(
    entry_points=[CommandHandler("shows", entry_point)],
    states={
        START: [
            CallbackQueryHandler(add_shows, pattern="^add_shows$"),
            CallbackQueryHandler(list_user_shows, pattern="^list_user_shows"),
            CallbackQueryHandler(track_add_progress, pattern="^track_progress_[0-9]+$")
        ],
        NEW_SHOW_SEARCH: [
            CallbackQueryHandler(stop, pattern="^quit$"),
            MessageHandler(filters=filters.TEXT, callback=search_sonarr_new)
        ],
        SHOW_PICKER: [
            CallbackQueryHandler(show_clicked, pattern="^add_show_[0-9]+$")
        ],
        TRACK_PROGRESS: [
            CallbackQueryHandler(stop, pattern="^quit$"),
            CallbackQueryHandler(track_add_progress, pattern="^track_progress_[0-9]+$")
        ],
        CONFIRM_SHOW: [
            CallbackQueryHandler(search_sonarr_new, pattern="^search_results$"),
            CallbackQueryHandler(confirm_show_add, pattern="^confirm_[0-9]+$"),
            CallbackQueryHandler(show_clicked, pattern="^add_show_[0-9]+$")
        ],
        CHOOSE_SHOW_TO_MANAGE: [
            CallbackQueryHandler(stop, pattern="^quit$"),
            CallbackQueryHandler(manage_show_menu, pattern="^manage_[0-9]+$"),
        ],
        MANAGE_SHOW: [
            CallbackQueryHandler(delete_show, pattern="^delete_[0-9]+$"),
            CallbackQueryHandler(manage_show_seaons, pattern="^man_season_[0-9]+$")
        ],
        MANAGE_SHOW_SEASON: [
            CallbackQueryHandler(stop, pattern="^quit$"),
            CallbackQueryHandler(add_show_season, pattern=f'show_[0-9]+_s_[0-9]+')
        ]
    },
    fallbacks=[CommandHandler("shows", entry_point)]
)
