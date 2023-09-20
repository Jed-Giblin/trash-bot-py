from pyarr import ReadarrAPI
from pyarr.exceptions import PyarrResourceNotFound


class ReadarrApi:
    def __init__(self, readarr_hostname, readarr_token, user=None, mypass=None, **kwargs):
        self._host = readarr_hostname
        self._api_key = readarr_token
        self._user = user
        self._pass = mypass
        self.__client = ReadarrAPI(f'https://{self._host}', self._api_key)
        if self._user and self._pass:
            self.__client.basic_auth(username=self._user, password=self._pass)

    def search_new_books(self, search_str):
        return self.__client.lookup(search_str)

    def manage_tags(self, tag):
        tags = next(filter(lambda x: x.get("label") == tag,
                           self.__client.get_tag()), None)

        if tags:
            return [tags.get('id')]
        else:
            return [self.__client.create_tag(tag).get('id')]

    def _add_book(self, book, tags):
        if not book.get('authorId'):
            author_data = self.__client.add_author(book.get('author'), root_dir=f'/books', author_monitor='none')
            author_data['monitored'] = True
            author_id = author_data.get('id')
            book = next(filter(lambda x: x.get("id") if book['foreignBookId'] == x['foreignBookId'] else {},
                               self.__client.lookup_book(term=book.get('title'))), {})
            for i in range(10):
                try:
                    author_set_monitor = self.__client.upd_author(author_id, author_data)
                    break
                except PyarrResourceNotFound:
                    ...
            book['author'] = author_set_monitor

        for tag in tags:
            if tag not in book['author']['tags']:
                book['author']['tags'].append(tag)
                self.__client.upd_author(book.get('authorId'), book.get('author'))

        if book.get('id'):
            book_update_monitor = self.__client.upd_book_monitor([book.get('id')])
            force_book_search = self.__client.post_command('BookSearch', bookIds=[book.get('id')])
        else:
            return False, 'Unable to find book ID'

        return True, 'ok'

    def add_book(self, book, user):
        tags = self.manage_tags(f'tg:{user}')

        return self._add_book(book, tags)

    def configure_notifications(self, user, bot_token):
        tags = self.manage_tags(f'tg:{user}')

        notification = next(filter(
            lambda x: x.get("id") if tags[0] in x.get('tags', []) and x.get('implementation') == 'Telegram' else None,
            self.__client.get_notification()), None)

        if not notification:
            schema = self.__client.get_notification_schema('Telegram').pop()
            schema['name'] = f'tg:{user}'
            schema['fields'] = [{'name': 'botToken', 'value': bot_token}, {'name': 'chatId', 'value': user}]
            schema['tags'].extend(tags)
            for x in ['onAuthorDelete', 'onBookFileDelete', 'onDownloadFailure', 'onReleaseImport', 'onImportFailure']:
                schema[x] = True
            self.__client.add_notification(schema)
