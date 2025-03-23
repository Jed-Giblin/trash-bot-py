import os
import json
import binascii
import pickle
import threading
from copy import deepcopy

from telegram.ext._picklepersistence import _BotUnpickler, PicklePersistence

from modules.db_models import TGUser, TGChat

DEFAULT_GROUP = {
    'words': [],
    'memes': False,
    'polls': [],
    'all': [],
    'name': ''
}


class UnallowedBlankValue(ValueError):
    pass


class EnhancedPicklePersistence(PicklePersistence):
    def lookup_user(self, code):
        return self.user_data[int(code)]

    def get_chat_list(self):
        return self.chat_data.values()

    def get_chat(self, chat_id):
        return self.chat_data[chat_id]

    def _load_users_from_json(self):
        print("Loading Users from JSON")
        if os.path.exists('./db/db.json'):
            with open('./db/db.json') as fh:
                json_data = json.loads(fh.read())
            for user_id, user in json_data.get("users").items():
                tg = TGUser.from_dict(**user)
                tg.id = int(user_id)
                self.user_data[tg.id] = tg

    def _load_chats_from_json(self):
        print("Loading Chats from JSON")
        if os.path.exists('./db/db.json'):
            with open('./db/db.json') as fh:
                json_data = json.loads(fh.read())
            for chat_id, chat in json_data.get("groups").items():
                tg = TGChat.from_dict(**chat)
                tg.id = int(chat_id)
                self.chat_data[tg.id] = tg

    def _load_singlefile(self) -> None:
        try:
            with self.filepath.open("rb") as file:
                data = _BotUnpickler(self.bot, file).load()
            self.user_data = data["user_data"]
            for user_id, tg in self.user_data.items():
                if 'book_cache' in tg:
                    tg['book_cache'] = {}
            self.chat_data = data["chat_data"]
            # For backwards compatibility with files not containing bot data
            self.bot_data = data.get("bot_data", self.context_types.bot_data())
            self.callback_data = data.get("callback_data", {})
            self.conversations = data["conversations"]
        except OSError:
            self.conversations = {}
            self.user_data = {}
            self._load_users_from_json()
            self.chat_data = {}
            self._load_chats_from_json()
            self.bot_data = {}
            self.callback_data = None
            if os.path.exists('./db/db.json'):
                os.rename('./db/db.json', './db/db.json.bak')
            else:
                os.makedirs('./db')
            self._dump_singlefile()
        except pickle.UnpicklingError as exc:
            filename = self.filepath.name
            raise TypeError(f"File {filename} does not contain valid pickle data") from exc
        except Exception as exc:
            print(exc)
            raise TypeError(f"Something went wrong unpickling {self.filepath.name}") from exc
