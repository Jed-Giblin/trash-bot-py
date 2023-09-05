import requests


class ReadarrApi:
    def __init__(self, readarr_hostname, readarr_token, user=None, mypass=None, **kwargs):
        self._host = readarr_hostname
        self._api_key = readarr_token
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

    def __put(self, path, body):
        uri = f'https://{self._host}{path}'
        res = requests.put(uri, params={"apiKey": self._api_key}, json=body)

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

    def get_url(self, url):
        return f'https://{self._host}{url}'

    def search_new_books(self, search_str):
        res = self.__get('/api/v1/search', params={'term': search_str}).json()
        return res

    def create_tag(self, tag):
        body = {"label": tag}
        return self.__post('/api/v1/tag', body=body).json().get("id")

    def manage_tags(self, tag):
        tags = next(filter(lambda x: x.get("label") == tag,
                           self.__get('/api/v1/tag').json()), None)

        if tags:
            return [tags.get("id")]
        else:
            return [self.create_tag(tag)]

    def _add_book(self, book, tags):
        author_exists = False
        author_check = self.__get(f'/api/v1/book/{book.get("id", 0)}')
        if author_check.status_code == 200:
            author_exists = True

        if author_exists:
            body = {"bookIds": [book['id']], "monitored": True}
            r = self.__put('/api/v1/book/monitor', body=body)
            force_refresh = self.__post('/api/v1/command', body={"name": "AuthorSearch", "authorId": book['authorId']})
        else:
            book["author"]["tags"] = tags
            book['author']['rootFolderPath'] = f'/books'
            book['author']['qualityProfileId'] = 1
            book['author']['monitored'] = True
            book['author']['metadataProfileId'] = 1
            book['author']['addOptions'] = {'monitor': 'none', 'monitored': True, 'searchForMissingBooks': False}

            book["tags"] = tags
            book['qualityProfileId'] = 1
            book['monitored'] = True
            book['addOptions'] = {'searchForNewBook': True, 'addType': 'automatic'}
            r = self.__post('/api/v1/book', body=book)

        if r:
            return True, 'ok'
        return False, r.text

    def add_book(self, book, user):
        tags = self.manage_tags(f'tg:{user}')

        return self._add_book(book, tags)
