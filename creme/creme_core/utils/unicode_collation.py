# This code it derived from :
#   pyuca - Unicode Collation Algorithm
#   Version: 2013-01-25
#   Author: James Tauber (http://jtauber.com/)
# found at: https://github.com/jtauber/pyuca

# Copyright (c) 2006-2013 James Tauber and contributors
# Copyright (c) 2013-2021 Hybird
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
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


"""
Preliminary implementation of the Unicode Collation Algorithm.

This only implements the simple parts of the algorithm but I have successfully
tested it using the Default Unicode Collation Element Table (DUCET) to collate
Ancient Greek correctly.

allkeys.txt (1.6 MB) is available at:
    http://www.unicode.org/Public/UCA/latest/allkeys.txt

but you can always subset this for just the characters you are dealing with.
"""

from logging import info
from re import compile as compile_re


class _Node:
    __slots__ = ('value', '_children')

    def __init__(self):
        self.value = None
        self._children = None  # Memory optimisation: children are created only if needed

    def get_next_node(self, key):
        next_node = None
        children = self._children

        if children:
            next_node = children.get(key)

        return next_node

    def set_next_node(self, key):
        children = self._children

        if children is None:
            self._children = children = {}

        return children.setdefault(key, _Node())


class _Collator:
    def __init__(self, filename=None):
        self._root = _Node()

        if filename is None:
            from os.path import dirname, join
            filename = join(dirname(__file__), 'allkeys.txt')

        # weights = {} #cache of (int, int, int, int) elements
        match = compile_re(
            r'^(?P<charList>[0-9A-F]{4,6}(?:[\s]+[0-9A-F]{4,6})*)[\s]*;[\s]*'
            r'(?P<collElement>(?:[\s]*\[(?:[\*|\.][0-9A-F]{4,6}){3,4}\])+)[\s]*'
            r'(?:#.*$|$)'
        ).match
        findall_ce = compile_re(r'\[.([^\]]+)\]?').findall  # 'ce' means 'collation element'
        add = self._add

        with open(filename) as f:
            for line in f:
                re_result = match(line)

                if re_result is not None:
                    group = re_result.group
                    add(
                        [int(ch, 16) for ch in group('charList').split()],
                        [
                            tuple(int(weight, 16) for weight in coll_element.split('.'))
                            for coll_element in findall_ce(group('collElement'))
                        ],
                    )
                elif not line.startswith(('#', '@')) and line.split():
                    info('ERROR in line %s:', line)

    def _add(self, key, value):
        curr_node = self._root

        for part in key:
            curr_node = curr_node.set_next_node(part)

        curr_node.value = value

    def _find_prefix(self, key):
        curr_node = self._root
        step = 0

        for part in key:
            next_node = curr_node.get_next_node(part)

            if next_node is None:
                break

            curr_node = next_node
            step += 1

        return curr_node.value, key[step:]

    def sort_key(self, string):
        find_prefix = self._find_prefix
        collation_elements = []
        extend = collation_elements.extend

        lookup_key = [ord(ch) for ch in string]
        while lookup_key:
            value, lookup_key = find_prefix(lookup_key)
            if not value:
                # Calculate implicit weighting for CJK Ideographs
                # contributed by David Schneider 2009-07-27
                # http://www.unicode.org/reports/tr10/#Implicit_Weights
                key = lookup_key[0]
                value = [
                    (0xFB40 + (key >> 15), 0x0020, 0x0002, 0x0001),
                    ((key & 0x7FFF) | 0x8000, 0x0000, 0x0000, 0x0000),
                ]
                lookup_key = lookup_key[1:]
            extend(value)

        sort_key = []
        append = sort_key.append

        for level in range(4):
            if level:
                append(0)  # Level separator

            for element in collation_elements:
                try:
                    ce_l = element[level]
                    if ce_l:
                        append(ce_l)
                except IndexError:
                    pass

        return tuple(sort_key)


collator = _Collator()
