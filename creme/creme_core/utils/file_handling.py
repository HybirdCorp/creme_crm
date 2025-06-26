################################################################################
#
# Copyright (c) 2016-2025 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

import logging
import os
import sys
from collections.abc import Iterable
from datetime import date, datetime
from os.path import exists, join, splitext
from random import randint

from ..utils.secure_filename import secure_filename

logger = logging.getLogger(__name__)


class FileNameSuffixGenerator:
    def __iter__(self):
        yield ''


class IncrFileNameSuffixGenerator(FileNameSuffixGenerator):
    def __iter__(self):
        i = 1

        while True:
            yield f'_{i}'
            i += 1


class RandomFileNameSuffixGenerator(FileNameSuffixGenerator):
    def __iter__(self):
        max_v = 16**8

        while True:
            yield f'_{randint(0, max_v):08x}'


class DateFileNameSuffixGenerator(FileNameSuffixGenerator):
    format = '%d%m%Y'

    def __iter__(self):
        yield f'_{date.today().strftime(self.format)}'


class DatetimeFileNameSuffixGenerator(FileNameSuffixGenerator):
    format = '%d%m%Y_%H%M%S'

    def __iter__(self):
        yield f'_{datetime.now().strftime(self.format)}'


# TODO: i18n for error messages ?
class FileCreator:
    """Creates new files atomically (does not reuse an existing ones)

    You provide a base name for the file, and if it already exists,
    it adds some suffixes as long as the new file names exist.

    It manages a maximum length, in order to be used straightforwardly with FileFields.
    """

    class Error(Exception):
        pass

    dir_path: str
    name: str
    max_trials: int
    max_length: int

    def __init__(self,
                 dir_path: str,
                 name: str,
                 generators: Iterable[type[FileNameSuffixGenerator]] = (
                     DatetimeFileNameSuffixGenerator,
                     IncrFileNameSuffixGenerator,
                 ),
                 max_trials: int = 1000,
                 max_length: int | None = None,
                 ):
        """Constructor.
        @param dir_path: Path of the directory where to create the files (string).
               The path must be valid on the current system.
               The directory is created (if it does not exist) by create().
        @param name: Base name of the future files. E.g. "foobar.txt"
        @param generators: iterable of FileNameSuffixGenerator instances.
        @param max_trials: number of file names trials before aborting.
               It's useful to avoid infinite (or very long) loops.
        @param max_length: Maximum length of the base name of the new file.
               It includes the extension, but not the directory.
               None means 'no max length'.
        """
        self.dir_path = dir_path
        self.name = name
        self.max_trials = max_trials
        self.max_length = max_length or sys.maxsize
        self._generators_classes: list[type[FileNameSuffixGenerator]] = [
            FileNameSuffixGenerator,
            *generators,
        ]

    def create(self) -> str:
        """Create a new file.
        @return The file path.
        @raise FileCreator.Error.
        """
        dir_path = self.dir_path
        if not exists(dir_path):
            try:
                os.makedirs(dir_path, 0o755)
            except OSError as e:
                if not exists(dir_path):
                    logger.warning('Cannot create directory %s (%s)', dir_path, e)

                    raise self.Error(
                        f'The directory {dir_path} cannot be created.'
                    ) from e

        name = secure_filename(self.name)
        name_root, name_ext = splitext(name)
        current_name_root = name_root
        max_trials = self.max_trials
        max_length = self.max_length - len(name_ext)
        trials = 0

        for generator_cls in self._generators_classes:
            for suffix in generator_cls():
                trials += 1

                root_max_len = max_length - len(suffix)
                if root_max_len < 0:
                    raise self.Error(
                        'No unique filename has been found with the '
                        'current rules (max length too short for suffix alone).'
                    )

                current_name_root = name_root[:root_max_len] + suffix
                final_path = join(dir_path, current_name_root + name_ext)

                try:
                    f = open(final_path, 'x')
                except FileExistsError as e:
                    if trials >= max_trials:
                        raise self.Error(
                            'No unique filename has been found with the '
                            'current rules (max trials reached).'
                        ) from e
                else:
                    f.close()

                    return final_path
            else:
                name_root = current_name_root  # We 'pipe' the name-generation rules.

        raise self.Error('No unique filename has been found with the current rules.')
