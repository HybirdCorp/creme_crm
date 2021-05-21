# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2020 Hybird
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
#
################################################################################
import glob
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

try:
    from enchant import DictWithPWL
    from enchant.checker import SpellChecker
    from enchant.tokenize import Filter, HTMLChunker
    enchant_loaded = True
except ImportError:
    enchant_loaded = False


try:
    import polib
    polib_loaded = True
except ImportError:
    polib_loaded = False


enchant_filters = []
if enchant_loaded:
    class PythonFormatFilter(Filter):
        def _skip(self, word):
            if word.startswith("«"):
                word = word[1:]
            if word.startswith("%("):
                return True
            if word.startswith("{"):
                return True
            if word[:2] == "#%":
                return True
            return False

    class HTMLFilter(Filter):
        exclude = {"&nbsp", "&ndash", "&nbsp;", "&ndash;"}

        def _skip(self, word):
            if word in self.exclude:
                return True
            return False

    enchant_filters = [HTMLFilter, PythonFormatFilter]
    enchant_chunkers = [HTMLChunker]


class Command(BaseCommand):
    help = ''
    args = ''
    source_language = "en"

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.checkers = {}

    def add_arguments(self, parser):
        parser.add_argument(
            '--allow-failures',
            action='store_true',
            help='The command will always exit with success',
        )

    def get_checker(self, language):
        if language in self.checkers:
            return self.checkers[language]

        personal_wordlist = os.path.join(settings.CREME_ROOT, "locale", f"pwl.{language}.txt")
        language_dict = DictWithPWL(language, pwl=personal_wordlist)
        checker = SpellChecker(language_dict, chunkers=enchant_chunkers, filters=enchant_filters)
        return checker

    def check_pofile(self, popath, source_language_checker):
        success_status = True
        rel = os.path.relpath(popath, settings.CREME_ROOT)
        pofile = polib.pofile(popath)

        try:
            po_language = pofile.metadata['Language']
            target_language_checker = self.get_checker(po_language)
        except KeyError:
            self.error(f"{rel} missing 'Language' metadata")
            po_language = None
            target_language_checker = None

        for entry in pofile:
            if entry.obsolete:
                continue

            # if entry.msgid:
            #     source_language_checker.set_text(entry.msgid)
            #     for err in source_language_checker:
            #         success_status = False
            #         self.stderr.write(f"{rel}:{entry.linenum} {self.source_language} {err.word}")
            #
            # if entry.msgid_plural:
            #     source_language_checker.set_text(entry.msgid_plural)
            #     for err in source_language_checker:
            #         success_status = False
            #         self.stderr.write(f"{rel}:{entry.linenum} {self.source_language} {err.word}")

            if target_language_checker is not None:
                if entry.msgstr:
                    target_language_checker.set_text(entry.msgstr)
                    for err in target_language_checker:
                        success_status = False
                        self.stderr.write(f"{rel}:{entry.linenum} {po_language} {err.word}")

                if entry.msgstr_plural:
                    for text in entry.msgstr_plural.values():
                        success_status = False
                        target_language_checker.set_text(text)
                        for err in target_language_checker:
                            self.stderr.write(f"{rel}:{entry.linenum} {po_language} {err.word}")
        return success_status

    def error(self, message):
        if self.raise_exception:
            raise CommandError(message)
        else:
            self.stderr.write(message)

    def handle(self, **options):
        self.raise_exception = not options.get('allow_failures')

        if not polib_loaded:
            self.error('The required "polib" library seems not installed ; aborting.')
            return

        if not enchant_loaded:
            self.error('The required "enchant" library seems not installed ; aborting.')
            return

        source_language_checker = self.get_checker(self.source_language)

        popaths = glob.iglob(os.path.join(settings.CREME_ROOT, "**/*.po"), recursive=True)

        success_status = True
        for popath in popaths:
            success_status &= self.check_pofile(popath, source_language_checker)

        if not success_status:
            self.error("Typos found")
