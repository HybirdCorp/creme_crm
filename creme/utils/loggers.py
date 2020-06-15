# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
import re
import time
from collections import defaultdict
from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARNING,
    Filter,
    Formatter,
    getLevelName,
)
from logging.handlers import TimedRotatingFileHandler
from os import makedirs
from os import remove as delete_file
from os import rename as rename_file
from os.path import dirname, exists, expanduser, join, splitext
from sys import path as syspath  # getfilesystemencoding
from threading import Thread

try:
    from termcolor import colored
except ImportError:
    def colored(str, *args, **kwargs):
        return str


class CremeFormatter(Formatter):
    _COLORS = defaultdict(lambda: (None, []), [
         (CRITICAL, ('magenta', ['bold'])),
         (ERROR,    ('red',     [])),
         (WARNING,  ('yellow',  [])),
         (INFO,     ('white',   [])),
         (DEBUG,    ('grey',    [])),
    ])

    def __init__(self, format=None, datefmt=None, colorize=False, colors=None):
        Formatter.__init__(self, fmt=format, datefmt=datefmt)
        cremepath = dirname(__file__)[:-len(join('creme', 'creme_core'))]

        self.prefixes = [
            ('', cremepath),
            *(('python-packages', path) for path in syspath),
        ]

        self.colorize = 'colored' in format
        self.colors = {**self._COLORS}

        if colors is not None:
            for key, color in colors.items():
                self.colors[getLevelName(key)] = color

    def formatModulepath(self, record):
        modulepath = splitext(record.pathname)[0]

        for prefix, path in self.prefixes:
            if modulepath.startswith(path):
                return modulepath.replace(path, prefix)

        return modulepath

    # TODO: remove ?
    def formatEncodedException(self, record):
        # exception = self.formatException(record.exc_info)
        #
        # for encoding in ['utf-8', getfilesystemencoding()]:
        #     try:
        #         return unicode(exception, encoding=encoding)
        #     except Exception:
        #         continue
        #
        # return str(exception, getfilesystemencoding(), errors='replace')
        return self.formatException(record.exc_info)

    def format(self, record):
        record.message = record.getMessage()
        record.modulepath = self.formatModulepath(record)
        record.asctime = self.formatTime(record, self.datefmt)

        if self.colorize:
            color, attrs = self.colors[record.levelno]
            record.colored_levelname = colored(getLevelName(record.levelno), color, attrs=attrs)

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatEncodedException(record)

        log = self._fmt % record.__dict__

        if record.exc_text:
            log = log if log.endswith('\n') else log + '\n'
            log = log + record.exc_text

        return log


class RegexFilter(Filter):
    def __init__(self, name='', pattern=None, exclude=False):
        Filter.__init__(self, name=name)
        self.pattern = re.compile(pattern) if pattern else None
        self.exclude = exclude

    def filter(self, record):
        if Filter.filter(self, record) == 0:
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
#    Copyright (C) 2009-2020  Hybird
#
#    This file is released under the Python License (http://www.opensource.org/licenses/Python-2.0)
################################################################################

class CompressedTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, *args, **kwargs):
        # filenames = kwargs.pop('filename', None)
        filename = kwargs.pop('filename', None)

        if filename is None:
            raise ValueError(
                f'{self.__class__.__name__} configuration is invalid (no "filename").'
            )

        # if isinstance(filenames, (list, tuple,)):
        #     self.filenames = (expanduser(p) for p in filenames[:1])
        # else:
        #     self.filenames = (expanduser(filenames),)

        # kwargs.update({'filename': self.filenames[0]})
        kwargs['filename'] = expanduser(filename)
        # super(CompressedTimedRotatingFileHandler, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

    # def _open(self):
    #     for filename in self.filenames:
    #         log_dir = dirname(filename)
    #         self.baseFilename = filename
    #
    #         try:
    #             if not exists(log_dir):
    #                 makedirs(log_dir)
    #
    #             return TimedRotatingFileHandler._open(self)
    #         except:
    #             continue
    #
    #     raise
    def _open(self):
        log_dir = dirname(self.baseFilename)

        if not exists(log_dir):
            makedirs(log_dir)

        # return super(CompressedTimedRotatingFileHandler, self)._open()
        return super()._open()

    def _next_filename(self, count, extension):
        for i in range(self.backupCount - 1, 0, -1):
            sfn = '{}.{}.gz'.format(self.baseFilename, i)
            dfn = '{}.{}.gz'.format(self.baseFilename, i + 1)

            if exists(sfn):
                if exists(dfn):
                    delete_file(dfn)

                rename_file(sfn, dfn)

            dfn = self.baseFilename + '.1.gz'

    def _now(self):
        return time.time()

    def _compute_next_rollover(self):
        currentTime = int(self._now())

        newRolloverAt = self.computeRollover(currentTime)

        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval

        # If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dstNow = time.localtime(currentTime)[-1]
            dstAtRollover = time.localtime(newRolloverAt)[-1]

            if dstNow != dstAtRollover:
                if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                    newRolloverAt = newRolloverAt - 3600
                else:           # DST bows out before next rollover, so we need to add an hour
                    newRolloverAt = newRolloverAt + 3600

        self.rolloverAt = newRolloverAt

    def _save_archive(self, rollover_filename):
        archive_filename = rollover_filename + '.bz2'
        backup_filename = rollover_filename + '.bak'
        bzip_file = None

        try:
            if exists(archive_filename):
                delete_file(archive_filename)

            with open(backup_filename, 'rb') as log_file:
                bzip_file = bz2.BZ2File(archive_filename, 'wb')
                bzip_file.writelines(log_file)
        except:
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
        rollover_timetuple = time.gmtime(rollover_timestamp) if self.utc else time.localtime(rollover_timestamp)

        rollover_filename = '{}-{}.log'.format(splitext(self.baseFilename)[0],
                                               time.strftime(self.suffix, rollover_timetuple),
                                              )

        if exists(self.baseFilename):
            # Backup current log file
            rename_file(self.baseFilename, rollover_filename + '.bak')

            # gzip backup log file
            self._deferred_save_archive(rollover_filename)

        # print("%s -> %s" % (self.baseFilename, dfn))
        self.mode = 'w'
        self.stream = self._open()
        self._compute_next_rollover()
