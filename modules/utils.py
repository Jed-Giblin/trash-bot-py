import logging

SEASON_UPDATE = {"monitored": False}


def manage_seasons(seasons):
    sorted_seasons = sorted(seasons, key=lambda s: s.get("seasonNumber"))
    edited_seasons = [{**season, **SEASON_UPDATE} for season in sorted_seasons]
    edited_seasons[-1]['monitored'] = True
    return edited_seasons


class ModTypes:
    CONVERSATION = 1
    COMMAND_DRIVEN = 2


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(asctime)s][%(process)s][%(levelname)s][%(filename)s:%(lineno)s][%(funcName)s()]: %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        """Sets the logging formatter details"""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class TrashLogger(object):
    """Singleton logging class to be used to keep logging levels and color across any script/lib"""

    def __init__(self, name, level=logging.INFO):
        """
        Generates a logger object that will be used across all scripts/libs that utilize this logging class

        :param name: The name to define this logger
        :param level: The logging level to use. Examples: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
        """
        self.logger = self.generate_logger(name, level=level)

    def generate_logger(self, name, level=logging.INFO):
        """Generates the logging handler

        :param name: The name to define this logger
        :param level: The logging level to use. Examples: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
        :return: :class:`Logger <Logger>` object
        """
        log = logging.getLogger(name)
        log.setLevel(level)
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(CustomFormatter())
        log.addHandler(log_handler)
        return log
