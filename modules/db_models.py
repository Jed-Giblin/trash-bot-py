from __future__ import annotations


class TGChat:
    def __init__(self, **kwargs):
        self.id = kwargs.get("chat_id", 0)
        self.words = kwargs.get("words", [])
        self.memes = kwargs.get("memes", [])
        self.polls = kwargs.get("polls", [])
        self.all = kwargs.get("all", [])
        self.name = kwargs.get("name", "")

    def __setstate__(self, repr):
        self.__dict__ = repr
        # Add new fields below this line

    @staticmethod
    def from_dict(**kwargs):
        chat = TGChat(**kwargs)
        return chat

    def add_trash_word(self, word):
        self.words.append(word)

    def remove_trash_word(self, word):
        self.words.remove(word)

    def save_poll(self, poll):
        self.polls.append(poll)


class TGUser:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 0)
        self.name = kwargs.get("name", "")
        self.sonarr_hostname = kwargs.get("sonarr_hostname", None)
        self.sonarr_token = kwargs.get("sonarr_token", None)
        self.radarr_hostname = kwargs.get("radarr_hostname", None)
        self.radarr_token = kwargs.get("radarr_token", None)
        self.readarr_hostname = kwargs.get("readarr_hostname", None)
        self.readarr_token = kwargs.get("readarr_token", None)
        self.del_msg_list = []

    def __setstate__(self, repr):
        self.__dict__ = repr
        # Add new fields below this line
        # If we are loading from Pickle, those messages that are pending delete might be old / drop them
        self.del_msg_list = []

    def __setitem__(self, key, item):
        self.__dict__[key] = item

    def __getitem__(self, key):
        return self.__dict__[key]

    def __delitem__(self, key):
        del self.__dict__[key]

    @staticmethod
    def from_dict(**kwargs):
        user = TGUser(**kwargs)
        return user

    def get_config(self):
        return f'Shows: {self.sonarr_hostname}, Movies: {self.radarr_hostname}, Books: {self.readarr_hostname}, Name: {self.name}'

    def save_servarr(self, prefix, name, token):
        setattr(self, f'{prefix}_hostname', name)
        setattr(self, f'{prefix}_token', token)

    def receive_access(self, from_user: TGUser):
        for attr in ['sonarr_hostname', 'sonarr_token', 'readarr_token', 'readarr_hostname', 'radarr_token',
                     'radarr_hostname']:
            setattr(self, attr, getattr(from_user, attr))

    def share(self):
        return hex(self.id)

    def get_sonarr_settings(self):
        """
        This is a wrapper to get sonarr settings. We can easily add to this dict, to pass my kwargs to the API constructor
        :return:
        """
        return {
            'host_url': f'https://{self.sonarr_hostname}', 'api_key': self.sonarr_token, 'ver_uri': '/v3'
        }

    def get_radarr_settings(self):
        return {
            'radarr_hostname': self.radarr_hostname, 'radarr_token': self.radarr_token
        }

    def get_readarr_settings(self):
        return {
            'readarr_hostname': self.readarr_hostname, 'readarr_token': self.readarr_token
        }
