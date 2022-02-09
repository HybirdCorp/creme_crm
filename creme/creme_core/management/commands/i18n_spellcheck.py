# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2022 Hybird
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
import array
import glob
import os
import re
from collections import defaultdict
from functools import partial

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand

from creme.creme_core.utils.unicode_collation import collator

try:
    from enchant import DictWithPWL
    from enchant.checker import SpellChecker
    enchant_loaded = True
except ImportError:
    enchant_loaded = False

try:
    import polib

    polib_loaded = True
except ImportError:
    polib_loaded = False


class CremePoTokenizer:
    def _to_string(self, word):
        if isinstance(word, array.array):
            return word.tounicode()
        return word

    def __init__(self, text):
        self._text = self._to_string(text)
        self._offset = 0

    def __next__(self):
        return self.next()

    def __iter__(self):
        return self

    replace_text = [
        ("&ndash;", ""),
        ("&nbsp;", ""),
        ("®", ""),
        ("©", ""),
        ("#", ""),
        ("%s", ""),
        ("%%d", ""),
        ("%d", ""),
        ("➔", ""),
        ("- ", ""),
        (" & ", " "),
        ("@/./+/-/_", ""),
        ("creme@crm.org", ""),
        ("creme@crm.com", ""),
        ("\n", " "),
    ]

    replace_patterns = [
        (re.compile(r"(%\()(.*?)(\)s)"), " "),
        (re.compile(r"[{](.*?)[}]"), " "),
        (re.compile(r'(\[)(.*?)(])'), r" \2 "),
        (re.compile(r'(\()(.*?)(\))'), r" \2 "),
        (re.compile(r"(')(.*?)(')"), r" \2 "),
        (re.compile(r'(")(.*?)(")'), r" \2 "),
        (re.compile(r'(«)(.*?)(»)'), r" \2 "),
        (re.compile(r'(“|”)(.*?)(“|”)'), r" \2 "),
    ]

    delimiters = re.compile(
        r":|;|,|\.|\s|/|!|\?|…|=|—|➔|≥|>|≤|<|\*|#|\+|%|-(\d+)|(n|N)°"
    )

    def looks_like_html(self, text):
        return "<" in text and ">" in text

    def parse_html(self, text):
        return BeautifulSoup(text, "html.parser").text

    def preprocess_text(self):
        text = self._text
        if self.looks_like_html(text):
            text = self.parse_html(text)
        for part, string in self.replace_text:
            text = text.replace(part, string)
        for pattern, string in self.replace_patterns:
            previous_text = ""
            new_text = text
            while previous_text != new_text:
                previous_text = new_text
                new_text = re.sub(pattern, string, previous_text)
            text = new_text
        text = re.split(self.delimiters, text)
        text = [word for word in text if word]
        self._text = text

    def next(self):
        offset = self._offset

        if offset == 0:
            self.preprocess_text()

        text = self._text
        if offset == len(text):
            raise StopIteration()

        pos = self._offset
        self._offset += 1

        return array.array("u", self._text[pos]), pos


class WordErrors(dict):
    def __init__(self):
        super().__init__(errors_count=0, files=defaultdict(list))

    def add_error(self, *, filename, line):
        self["errors_count"] += 1
        self["files"][filename].append(str(line))


class LanguageErrors(dict):
    def __init__(self):
        super().__init__(errors_count=0, words=defaultdict(WordErrors))

    def add_error(self, *, word, filename, line):
        self["errors_count"] += 1
        self["words"][word].add_error(filename=filename, line=line)


class ErrorDict(dict):
    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(errors_count=0, languages=defaultdict(LanguageErrors))

    def add_error(self, *, language, word, filename, line):
        self["errors_count"] += 1
        self["languages"][language].add_error(word=word, filename=filename, line=line)

    def report(self, raise_exception):
        if not self["errors_count"]:
            self.stdout.write("No error found!")
            return

        sort_key = collator.sort_key
        self.stderr.write(f"Found a total of {self['errors_count']} errors")
        for language_code, language_errors in self["languages"].items():
            self.stderr.write(f"Language «{language_code}» ({language_errors['errors_count']}):")

            words = list(language_errors["words"])
            words.sort(key=lambda word: sort_key(word))

            for word in words:
                word_errors = language_errors["words"][word]
                self.stderr.write(f"\t «{word}» ({word_errors['errors_count']}):")
                for filename, lines in word_errors["files"].items():
                    self.stderr.write(f"\t\t{filename} : {', '.join(lines)}")
        if raise_exception:
            exit(1)


class Command(BaseCommand):
    help = 'Scan PO files for typos'
    args = ''
    source_language = "en"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkers = {}
        self.errors = ErrorDict(self.stdout, self.stderr)

    def add_arguments(self, parser):
        parser.add_argument(
            '--allow-failures',
            action='store_true',
            help='The command will always exit with success',
        )

    def get_checker(self, language):
        if language in self.checkers:
            return self.checkers[language]

        # File containing words to consider valid
        personal_word_list = os.path.join(settings.CREME_ROOT, "locale", f"pwl.{language}.txt")
        language_dict = DictWithPWL(language, pwl=personal_word_list)

        self.stdout.write(
            f"Spellchecking language «{language}» with {language_dict.provider.desc}")

        checker = SpellChecker(language_dict, tokenize=CremePoTokenizer)
        self.checkers[language] = checker
        return checker

    def error(self, message, raise_exception):
        self.stderr.write(message)
        if raise_exception:
            exit(1)

    def check_entry(self, *, language, checker, filename, message, linenum):
        if message:
            checker.set_text(message)
            for err in checker:
                self.errors.add_error(
                    language=language,
                    word=err.word,
                    filename=filename,
                    line=linenum,
                )

    def handle(self, **options):
        raise_exception = not options.get('allow_failures')

        if not polib_loaded:
            self.error(
                'The required "polib" library seems not installed ; aborting.',
                raise_exception)
            return

        if not enchant_loaded:
            self.error(
                'The required "enchant" library seems not installed ; aborting.',
                raise_exception)
            return

        po_filepaths = list(
            glob.iglob(os.path.join(settings.CREME_ROOT, "**/*.po"), recursive=True))

        source_language_checker = self.get_checker(self.source_language)

        for po_filepath in po_filepaths:
            po_file = polib.pofile(po_filepath)
            relative_po_file_path = os.path.relpath(po_filepath, settings.CREME_ROOT)
            check_source = partial(
                self.check_entry,
                language=self.source_language,
                checker=source_language_checker,
                filename=relative_po_file_path,
            )

            try:
                target_language = po_file.metadata['Language']
                target_language_checker = self.get_checker(target_language)
            except KeyError:
                self.error(
                    f"{relative_po_file_path} is missing the 'Language' metadata",
                    raise_exception)
                target_language = None
                target_language_checker = None

            check_target = partial(
                self.check_entry,
                language=target_language,
                checker=target_language_checker,
                filename=relative_po_file_path,
            )
            for entry in po_file:
                if entry.obsolete:
                    continue
                check_source(message=entry.msgid, linenum=entry.linenum)
                check_source(message=entry.msgid_plural, linenum=entry.linenum)
                if target_language_checker is not None:
                    check_target(message=entry.msgstr, linenum=entry.linenum)
                    for message in entry.msgstr_plural.values():
                        check_target(message=message, linenum=entry.linenum)

        self.errors.report(raise_exception=raise_exception)
