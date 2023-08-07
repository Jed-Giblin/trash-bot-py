import requests

from modules.utils import manage_seasons


class SonarrApi:
    def __init__(self, sonarr_hostname, sonarr_token, user=None, mypass=None, **kwargs):
        self._host = sonarr_hostname
        self._api_key = sonarr_token
        self._user = user
        self._pass = mypass

    def __auth(self):
        return self._user, self._pass

    def __get(self, path, params=None):
        if params is None:
            params = dict()
        uri = f'https://{self._host}{path}'
        if 'apiKey' not in params:
            params['apiKey'] = self._api_key
        return requests.get(uri, params=params, auth=self.__auth())

    def __post(self, path, body):
        uri = f'https://{self._host}{path}'
        res = requests.post(uri, params={"apiKey": self._api_key}, json=body)
        if res.status_code >= 400:
            #TODO - Convert to logging
            print(f'Got Status Code: {res.status_code} when POSTing to {uri}')
            print(f'Got Body: {res.json()}')
            if res.status_code == 400:
                raise ValueError(res.json()[0]['errorMessage'])
            if res.status_code == 401 or res.status_code == 403:
                raise PermissionError
            raise ValueError("There was a failure communicating with the server")
        return res

    def search(self, query_str):
        res = self.__get('/api/series/lookup', params={"term": query_str})
        return res.json()

    def create_tag(self, tag):
        body = {"label": tag}
        return self.__post('/api/tag', body=body).json().get("id")

    def manage_tags(self, tag):
        tags = next(filter(lambda x: x.get("label") == tag,
                           self.__get('/api/tag').json()), None)

        if tags:
            return [tags.get("id")]
        else:
            return [self.create_tag(tag)]

    def _add_show(self, show, seasons, tags):
        body = {
            'tvdbId': show.get("tvdbId"),
            'title': show.get("title"),
            'profileId': 1,
            'titleSlug': show.get("titleSlug"),
            'images': show.get("images"),
            'seasons': seasons,
            'RootFolderPath': '/tv',
            'seasonFolder': True,
            'tags': tags,
            'addOptions': {'ignoreEpisodesWithoutFiles': False, 'ignoreEpisodesWithFiles': False}
        }
        if self.__post('/api/series', body=body):
            return True
        return False

    def add_show(self, show, user_id):
        seasons = manage_seasons(show.get("seasons"))
        tags = self.manage_tags(f'tg:{user_id}')
        try:
            return self._add_show(show, seasons, tags), 'ok'
        except Exception as ex:
            return False, ex
