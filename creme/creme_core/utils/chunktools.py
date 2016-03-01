# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from future_builtins import map

#def iter_splitchunks(chunks, sep, filter):
def iter_splitchunks(chunks, sep, parser=None, limit=None):
    """ Iterator through chunks as split single stream.

    @param chunks: iterator of list of strings
    @param sep: split separator
    @param parser: function that returns a parsed result from each entry.
                   if returns None, False or empty string, the entry will be ignored
    @param limit: single line length limit. throw a ValueError if reached.
    """
    overflow = ''

    for chunk in chunks:
        lines = (overflow + chunk).split(sep)
        overflow = lines[-1]

        if limit is not None and len(lines[0]) > limit:
            raise ValueError('line length is over %d characters' % limit)

        entries = map(parser, lines[:-1]) if parser is not None else lines[:-1]

        for entry in entries:
            if entry:
                yield entry

    last = parser(overflow) if parser is not None else overflow

    if last:
        yield last


def iter_splitlinechunks(chunks, parser=None, limit=None):
    overflow = ''
    endline = '\r\n'

    for chunk in chunks:
        lines = (overflow + chunk).splitlines(True)
        overflow = lines[-1]

        if limit is not None and len(lines[0].rstrip(endline)) > limit:
            raise ValueError('line length is over %d characters' % limit)

        entries = [l.rstrip(endline) for l in lines[:-1]]
        entries = map(parser, entries) if parser is not None else entries

        for line in entries:
            if line:
                yield line

    last = parser(overflow) if parser is not None else overflow

    if last:
        yield last


def iter_as_chunk(iterable, step):
    """Iterator which returns chunks from an iterable.
    @param iterable: iterator
    @param step: chunks size
    """
    chunk = []

    for index, item in enumerate(iterable):
        if not index % step and chunk:
            yield chunk
            chunk = []

        chunk.append(item)

    if chunk:
        yield chunk


def iter_as_slices(iterable, step):
    """ Iterator that returns chunks from an iterable using slices (useful for requests)
    @param iterable: iterator
    @param step: chunks size
    """
    index = 0

    while index != -1:
        chunk = iterable[index:index + step]
        chunk_length = len(chunk)

        index = index + step if chunk_length == step else -1

        if chunk_length:
            yield chunk
