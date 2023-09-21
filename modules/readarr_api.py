from time import sleep

from pyarr import ReadarrAPI
from pyarr.exceptions import PyarrResourceNotFound
from .utils import TrashLogger


class ReadarrApi:
    def __init__(self, readarr_hostname, readarr_token, user=None, mypass=None, **kwargs):
        self.logger = TrashLogger(name=self.__class__.__name__).logger
        self._host = readarr_hostname
        self._api_key = readarr_token
        self._user = user
        self._pass = mypass
        self.__client = ReadarrAPI(f'https://{self._host}', self._api_key)
        if self._user and self._pass:
            self.__client.basic_auth(username=self._user, password=self._pass)

    def search_books(self, search_str):
        self.logger.info(f'Performing lookup. Term: "{search_str}"')
        results = self.__client.lookup(search_str)
        self.logger.info(f'Found {len(results)} results for "{search_str}"')
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
            self.logger.info(f'Author Added: {author_data.get("authorName")} (ID: {author_data.get("id")})')
            author_data['monitored'] = True
            author_id = author_data.get('id')
            self.logger.info('Waiting for author metadata to update')
            sleep(5)

            search_results = self.search_books(book.get('title'))
            book = next(
                filter(lambda x: x.get('book', {}).get('foreignBookId') == book.get('foreignBookId'), search_results),
                {}).get('book')
            if not book:
                return False, 'Failed book lookup to Readarr API. Please try again later.'

            for i in range(10):
                try:
                    author_set_monitor = self.__client.upd_author(author_id, author_data)
                    book['author'] = author_set_monitor
                    self.logger.info(f'Author ID ({author_id}) Set to Monitored')
                    break
                except PyarrResourceNotFound as e:
                    self.logger.error(e)
                    sleep(1)
        else:
            self.logger.info(f'Author {book.get("author", {}).get("authorName")} (ID: {book.get("authorId")}) exists,'
                  f' skipping add.')

        for tag in tags:
            if tag not in book['author']['tags']:
                book['author']['tags'].append(tag)
                self.__client.upd_author(book.get('author', {}).get('id'), book.get('author'))

        if book.get('id'):
            book_update_monitor = self.__client.upd_book_monitor([book.get('id')])
            force_book_search = self.__client.post_command('BookSearch', bookIds=[book.get('id')])
            self.logger.info(f'Added {book.get("title")} (ID: {book.get("id")}) to monitoring and triggered a search')
        else:
            return False, 'Unable to find book ID'

        return True, 'ok'

    def add_book(self, book, user):
        tags = self.manage_tags(f'tg:{user}')
        return self._add_book(book, tags)

    def configure_notifications(self, user, bot_token):
        tags = self.manage_tags(f'tg:{user}')

        notification = next(filter(lambda x: tags[0] in x.get('tags', []) and x.get('implementation') == 'Telegram',
                                   self.__client.get_notification()), None)

        if not notification:
            schema = self.__client.get_notification_schema('Telegram').pop()
            schema['name'] = f'tg:{user}'
            schema['fields'] = [{'name': 'botToken', 'value': bot_token}, {'name': 'chatId', 'value': user}]
            schema['tags'].extend(tags)
            for x in ['onAuthorDelete', 'onBookFileDelete', 'onDownloadFailure', 'onReleaseImport', 'onImportFailure']:
                schema[x] = True
            self.__client.add_notification(schema)
