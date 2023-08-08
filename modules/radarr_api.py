import requests


class RadarrApi:
    def __init__(self, radarr_hostname, radarr_token, user=None, mypass=None, **kwargs):
        self._host = radarr_hostname
        self._api_key = radarr_token
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

    def search_new_movies(self, search_str):
        res = self.__get('/api/v3/movie/lookup', params={'term': search_str}).json()
        return res
