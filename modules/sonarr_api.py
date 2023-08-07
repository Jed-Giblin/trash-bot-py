import requests


class SonarrApi:
    def __init__(self, sonarr_hostname, sonarr_token, user=None, mypass=None, **kwargs):
        self._host = sonarr_hostname
        self._api_key = sonarr_token
        self._user = user
        self._pass = mypass

    def __auth(self):
        return self._user, self._pass

    def search(self, query_str):
        uri = f'https://{self._host}/api/series/lookup'
        res = requests.get(uri, params={"term": query_str, "apiKey": self._api_key}, auth=self.__auth())
        return res.json()
