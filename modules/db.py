import os
import json
import binascii
import threading


class UnallowedBlankValue(ValueError):
    pass


class Db:
    def __init__(self, base_path="."):
        self._dir = f'{base_path}/db'
        if not os.path.exists(self._dir):
            os.makedirs(self._dir)
        self._dbf = f'{self._dir}/db.json'
        if not os.path.exists(self._dbf):
            with open(self._dbf, 'w+') as fh:
                fh.write('{"users": {}, "groups": {}}')

        with open(self._dbf) as fh:
            self.db = json.load(fh)

        self.migrate()
        self.timer = threading.Timer(30.0, self.setup_saver)
        self.timer.start()

    def setup_saver(self):
        self.timer = threading.Timer(30.0, self.setup_saver)
        self.timer.start()

    def save(self):
        with open(self._dbf, 'w') as fh:
            fh.write(json.dumps(self.db))

    def handle_exit(self):
        self.save()
        self.timer.cancel()

    def migrate(self):
        migrations = []
        for migration in migrations:
            pass

    def share_code_is_valid(self, code):
        return next(
            filter(lambda u: u["share"] == code, self.db.get("users").values())
            , None) is not None

    def get_user_by_code(self, code):
        return next(
            filter(lambda u: u["share"] == code, self.db.get("users").values())
            , None)

    def share_access(self, user_id, code):
        uid = str(user_id)
        self.db.get("users")[uid] = self.get_user_by_code(code)

    def get_user(self, user_id):
        return self.db.get("users")[str(user_id)]

    def save_user_configuration(self, user_id, **kwargs):
        uid = str(user_id)
        if uid not in self.db.get("users"):
            self.db['users'][uid] = {}

        self.db['users'][uid].update(kwargs)
        if 'share' not in self.db['users'][uid]:
            self.__set_user_share(uid)
        return self.db['users'][uid]['share']

    def get_group(self, group_id):
        if group_id in self.db.get('groups'):
            return self.db['groups'][str(group_id)]
        return None

    def save_group(self, group_id, **kwargs):
        if group_id not in self.db.get('groups'):
            self.db['groups'][group_id] = {}

        self.db['groups'][group_id].update(kwargs)
        self.save()
        return self.db['groups'][group_id]

    def get_chat_list(self):
        return list(self.db.get("groups").keys())

    def __set_user_share(self, user_id):
        self.db['users'][user_id]['share'] = binascii.b2a_hex(os.urandom(8)).decode()


db = None
if not db:
    print("Init DB")
    db = Db()
