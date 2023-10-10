import os

import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, \
    MessageHandler, filters

from modules.readarr_api import ReadarrApi
from modules.utils import ModTypes

MOD_TYPE = ModTypes.CONVERSATION
MAIN_MENU = 1
END = 2

COMMAND = 'books'

NEW_BOOK_SEARCH = 11
SELECT_SEARCH_RESULT = 21
CONFIRM_BOOK_OR_SELECT_NEW = 22


async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "That's only allowed in private chats.", quote=True
        )
        return ConversationHandler.END
    reply_keyboard = [
        ["Add Books"],
        ["Manage Books"],
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


async def manage_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        text='Sorry, I haven"t set this up yet', chat_id=update.effective_chat.id
    )
    return ConversationHandler.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO - Empty context
    await update.callback_query.answer()
    await update.callback_query.message.edit_text('Goodbye', reply_markup=None)
    return ConversationHandler.END


async def add_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        reply_to_message_id=update.message.id, quote=True,
        text="Whats the book name you want to add? Send me a message with its name. You can also press quit.",
        allow_sending_without_reply=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Quit", callback_data="quit")]])
    )

    return NEW_BOOK_SEARCH


async def list_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_str = update.message.text
    readarr_config = context.user_data.get_readarr_settings()
    context.user_data['readarr'] = ReadarrApi(**readarr_config)
    context.user_data['book_cache'] = {}
    context.user_data['downloads'] = []

    await context.bot.send_message(
        text=f'Beginning search for "{search_str}". This may take up to a minute while results are compiled.',
        chat_id=update.effective_chat.id
    )

    btns = [[InlineKeyboardButton(text="Quit! (not a book)", callback_data=f'quit')]]
    found_books = False
    for book in sorted(context.user_data['readarr'].search_books(search_str),
                       key=(lambda x: x.get('book', {}).get('ratings', {}).get('value', 0)), reverse=True)[
                0:50]:
        book = book.get('book')
        if not book:
            continue
        bk_id = str(book['foreignBookId'])
        context.user_data['book_cache'][bk_id] = book
        author = book.get("author", {}).get("authorNameLastFirst", "")
        slug = f'{book["title"]}'
        if book["seriesTitle"]:
            slug = f'{slug} ({book["seriesTitle"]})'
        slug = f'{slug} - {author}'
        btns.append([InlineKeyboardButton(text=slug, callback_data=f"detail_{bk_id}")])
        found_books = True

    if found_books:
        text_content = 'Here are the top results. You can also search again by sending me a new message'
    else:
        text_content = 'Search returned no results at this time, please try again or use a different search term'

    await context.bot.send_message(
        text=text_content,
        chat_id=update.effective_chat.id,
        reply_markup=InlineKeyboardMarkup(btns)
    )
    return SELECT_SEARCH_RESULT


async def detail_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = str(query.data.split('_')[-1])

    book = context.user_data['book_cache'][book_id]
    if book.get("images"):
        poster_url = book.get("images")[0].get("url")
        context.user_data['downloads'].append(write_file(f'./tmp/books', f'{book_id}.jpg', poster_url))
        with open(f'./tmp/books/{book_id}.jpg', 'rb') as f:
            await context.bot.send_photo(update.effective_chat.id, photo=f)
    author = book.get("author", {}).get("authorNameLastFirst", "")
    book_str = f'{book["title"]}'
    if book["seriesTitle"]:
        book_str = f'{book_str} ({book["seriesTitle"]})'
    rating = book.get('ratings', {}).get('value', 0)
    book_str = f"{book_str} - {author}\n\n{book.get('overview', '')}\n\nRating: {rating}\nForeign Book ID: {book_id}\n" \
               f"Imported Book ID: {book.get('id')}\nAuthor Id: {book.get('authorId')}"
    btns = [InlineKeyboardButton("Click here to add", callback_data=f"confirm_{book_id}")]
    await context.bot.send_message(
        text=book_str,
        chat_id=update.effective_chat.id,
        reply_markup=InlineKeyboardMarkup([btns])
    )
    return CONFIRM_BOOK_OR_SELECT_NEW


async def confirm_book_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_message(
        text='Please wait while your book is added to monitoring. This may take a up to a minute while the author '
             'and title are being added.',
        chat_id=update.effective_chat.id
    )
    book_id = str(query.data.split('_')[-1])
    book = context.user_data['book_cache'][book_id]
    try:
        context.user_data['readarr'].add_book(book, str(update.effective_chat.id))
        await context.bot.send_message(
            text='Book added to monitoring. Searching will begin shortly.', chat_id=update.effective_chat.id
        )
    except ValueError as ex:
        await context.bot.send_message(
            text=f'Unable to add book. {ex}', chat_id=update.effective_chat.id
        )
    return ConversationHandler.END


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
            MessageHandler(filters.Regex("^Add Books$"), callback=add_books),
            MessageHandler(filters.Regex("^Manage Books$"), callback=manage_books),
        ],
        NEW_BOOK_SEARCH: [
            MessageHandler(filters=filters.TEXT, callback=list_search_results),
            CallbackQueryHandler(stop, pattern="^quit$")
        ],
        SELECT_SEARCH_RESULT: [
            CallbackQueryHandler(stop, pattern="^quit$"),
            CallbackQueryHandler(detail_book, pattern='^detail_[0-9]+$'),
            MessageHandler(filters=filters.TEXT, callback=list_search_results)
        ],
        CONFIRM_BOOK_OR_SELECT_NEW: [
            CallbackQueryHandler(stop, pattern="^quit$"),
            CallbackQueryHandler(confirm_book_add, pattern="^confirm_[0-9]+$"),
            CallbackQueryHandler(detail_book, pattern='^detail_[0-9]+$')
        ]
    },
    fallbacks=[CommandHandler("books", entry_point)]
)
