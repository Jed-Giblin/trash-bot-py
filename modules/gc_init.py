from typing import Optional, Tuple

from telegram import Update, ChatMember, ChatMemberUpdated, Chat
from telegram.ext import CommandHandler, ContextTypes, ChatMemberHandler
from modules.db import db as mydb

from modules.utils import ModTypes

MOD_TYPE = ModTypes.COMMAND_DRIVEN


def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member


async def gc_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        await update.message.reply_text(
            'This command is only for group chats'
        )
        return None
    else:
        chat_id = update.effective_chat.id
        if mydb.get_or_create_chat(chat_id, update.effective_chat.title):
            await update.message.reply_text(
                'Got it champ'
            )
        else:
            await update.message.reply_text(
                "Not Needed"
            )


async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result
    chat = update.effective_chat
    if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        return None

    if not is_member and not was_member:
        # How did this happen?
        return None

    if was_member and not is_member:
        mydb.delete_chat(str(chat.id))
        return None

    mydb.get_or_create_chat(chat.id, chat.title)


HANDLERS = [
    CommandHandler("gcsetup", gc_setup),
    ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER)
]
