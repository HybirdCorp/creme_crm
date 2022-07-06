################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import bz2
import logging
import re
import time
from logging import getLevelName
from logging.handlers import TimedRotatingFileHandler
from os import makedirs
from os import remove as delete_file
from os import rename as rename_file
from os.path import dirname, exists, expanduser, splitext
from sys import path as syspath
from threading import Thread

from django.core.exceptions import ImproperlyConfigured
from django.utils import termcolors


class CremeFormatter(logging.Formatter):
    DARK_PALETTE = 'dark'
    LIGHT_PALETTE = 'light'
    PALETTES = {
        DARK_PALETTE: {
            logging.CRITICAL: {'fg': 'magenta', 'opts': ('bold',)},
            logging.ERROR:    {'fg': 'red'},
            logging.WARNING:  {'fg': 'yellow'},
            logging.INFO:     {'fg': 'white', 'opts': ('bold',)},
            logging.DEBUG:    {'fg': 'white'},
        },
        LIGHT_PALETTE: {
            logging.CRITICAL: {'fg': 'magenta', 'opts': ('bold',)},
            logging.ERROR:    {'fg': 'red'},
            logging.WARNING:  {'fg': 'yellow', 'opts': ('bold',)},
            logging.INFO:     {'fg': 'black', 'opts': ('bold',)},
            logging.DEBUG:    {'fg': 'black'},
        }
    }

    def __init__(self, format=None, datefmt=None, palette=DARK_PALETTE):
        super().__init__(fmt=format, datefmt=datefmt)
        self.prefixes = [
            ('', dirname(dirname(dirname(__file__)))),  # creme's path
            *(('python-packages', path) for path in syspath),
        ]
        self.colorize = colorize = 'colored' in format

        if colorize:
            if isinstance(palette, str):
                palette = self.PALETTES[palette]
            else:
                if not isinstance(palette, dict):
                    raise ImproperlyConfigured(
                        'The "palette" argument for the logging configuration must be a dict'
                    )

            self._colorizators = {
                level: termcolors.make_style(**kw)
                for level, kw in palette.items()
            }

    def formatModulepath(self, record):
        module_path = splitext(record.pathname)[0]

        for prefix, path in self.prefixes:
            if module_path.startswith(path):
                return module_path.replace(path, prefix)

        return module_path

    def format(self, record):
        record.message = record.getMessage()
        record.modulepath = self.formatModulepath(record)
        record.asctime = self.formatTime(record, self.datefmt)

        if self.colorize:
            level = record.levelno
            record.colored_levelname = self._colorizators[level](getLevelName(level))

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        log = self._fmt % record.__dict__

        if record.exc_text:
            log = log if log.endswith('\n') else log + '\n'
            log += record.exc_text

        return log


class RegexFilter(logging.Filter):
    def __init__(self, name='', pattern=None, exclude=False):
        super().__init__(name=name)
        self.pattern = re.compile(pattern) if pattern else None
        self.exclude = exclude

    def filter(self, record):
        if super().filter(record) == 0:
            return 0

        if self.pattern:
            match = self.pattern.match(record.getMessage()) is not None
            match = not match if self.exclude else match
            return 1 if match else 0

        return 1


################################################################################
#    This code is derived from the TimedRotatingFileHandler of module
#    logging/handlers.py of the Python2.7 standard library.
#
#    Copyright 2001-2007 by Vinay Sajip. All Rights Reserved.
#
#    Copyright (C) 2009-2022  Hybird
#
#    This file is released under the Python License (http://www.opensource.org/licenses/Python-2.0)
################################################################################

class CompressedTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, *args, **kwargs):
        filename = kwargs.pop('filename', None)

        if filename is None:
            raise ValueError(
                f'{self.__class__.__name__} configuration is invalid (no "filename").'
            )

        kwargs['filename'] = expanduser(filename)
        super().__init__(*args, **kwargs)

    def _open(self):
        log_dir = dirname(self.baseFilename)

        if not exists(log_dir):
            makedirs(log_dir)

        return super()._open()

    def _now(self):
        return time.time()

    def _compute_next_rollover(self):
        current_time = int(self._now())
        new_rollover_at = self.computeRollover(current_time)

        while new_rollover_at <= current_time:
            new_rollover_at = new_rollover_at + self.interval

        # If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dst_now = time.localtime(current_time)[-1]
            dst_at_rollover = time.localtime(new_rollover_at)[-1]

            if dst_now != dst_at_rollover:
                if not dst_now:
                    # DST kicks in before next rollover, so we need to deduct an hour
                    new_rollover_at = new_rollover_at - 3600
                else:
                    # DST bows out before next rollover, so we need to add an hour
                    new_rollover_at = new_rollover_at + 3600

        self.rolloverAt = new_rollover_at

    def _save_archive(self, rollover_filename):
        archive_filename = f'{rollover_filename}.bz2'
        backup_filename  = f'{rollover_filename}.bak'
        bzip_file = None

        try:
            if exists(archive_filename):
                delete_file(archive_filename)

            with open(backup_filename, 'rb') as log_file:
                bzip_file = bz2.BZ2File(archive_filename, 'wb')
                bzip_file.writelines(log_file)
        except Exception:  # TODO: better exceptions ??
            pass
        else:
            delete_file(backup_filename)
        finally:
            if bzip_file:
                bzip_file.close()

            # Clean up oldest files
            self._cleanup_oldest()

    def _deferred_save_archive(self, rollover_filename):
        try:
            thread = Thread(target=self._save_archive, args=(rollover_filename,))
            thread.start()
        finally:
            # Clean up oldest files
            self._cleanup_oldest()

    def _cleanup_oldest(self):
        if self.backupCount > 0:
            for filename in self.getFilesToDelete():
                delete_file(filename)

    def doRollover(self):
        if self.stream and not self.stream.closed:
            self.stream.close()

        # Get the time that this sequence started at and make it a TimeTuple
        rollover_timestamp = self.rolloverAt - self.interval
        rollover_timetuple = (
            time.gmtime(rollover_timestamp)
            if self.utc else
            time.localtime(rollover_timestamp)
        )

        rollover_filename = '{}-{}.log'.format(
            splitext(self.baseFilename)[0],
            time.strftime(self.suffix, rollover_timetuple),
        )

        if exists(self.baseFilename):
            # Backup current log file
            rename_file(self.baseFilename, f'{rollover_filename}.bak')

            # Compress backup log file
            self._deferred_save_archive(rollover_filename)

        self.mode = 'w'
        self.stream = self._open()
        self._compute_next_rollover()
