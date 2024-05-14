import requests

from modules.utils import manage_seasons


class SonarrApi:
    def __init__(self, sonarr_hostname, sonarr_token, user=None, mypass=None, **kwargs):
        if not sonarr_hostname or not sonarr_token or sonarr_hostname == '' or sonarr_token == '':
            raise ValueError
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

    def __delete(self, path, params=None):
        if params is None:
            params = dict()
        uri = f'https://{self._host}{path}'
        if 'apiKey' not in params:
            params['apiKey'] = self._api_key
        return requests.delete(uri, params=params, auth=self.__auth())

    def __post(self, path, body):
        uri = f'https://{self._host}{path}'
        res = requests.post(uri, params={"apiKey": self._api_key}, json=body)
        if res.status_code >= 400:
            # TODO - Convert to logging
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

    def search_existing_shows_by_tag(self, tag):
        """
        1. Get the ID for the tag
        2. Fetch usage of tag
        3. Fetch series in use by that tag
        :param tag:
        :return:
        """
        tags = next(filter(lambda x: x.get("label") == tag,
                           self.__get('/api/tag').json()), None)
        if not tags:
            return []

        detail = self.__get(f'/api/v3/tag/detail/{tags.get("id")}').json()
        if not detail:
            return []
        series = [series for series in self.__get(f'/api/v3/series').json() if series["id"] in detail['seriesIds']]
        return series

    def search_for_episodes(self, series_id):
        res = self.__post('/api/command', body={'name': 'SeriesSearch', 'seriesId': series_id})
        return res.json()

    def delete_show(self, series_id):
        res = self.__delete(f'/api/v3/series/{series_id}', params={'deleteFiles': True})
        return res

    def get_show(self, series_id):
        res = self.__get(f'/api/v3/series/{series_id}')
        return res.json()

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
            'monitored': True,
            'addOptions': {'ignoreEpisodesWithoutFiles': False, 'ignoreEpisodesWithFiles': False}
        }
        res = self.__post('/api/series', body=body)
        if res:
            return True, res.json()
        return False, {}

    def add_show(self, show, user_id):
        seasons = manage_seasons(show.get("seasons"))
        tags = self.manage_tags(f'tg:{user_id}')
        try:
            success, res = self._add_show(show, seasons, tags)
            return success, 'ok', res
        except Exception as ex:
            return False, ex, {}
