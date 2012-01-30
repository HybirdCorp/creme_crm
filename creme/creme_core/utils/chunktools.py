# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

def iter_splitchunks(chunks, sep, filter):
    """ Iterator through chunks as split single stream.

    TODO : add limitation to overflow. if the separator doesn't exist in many following chunks,
    the overflow string will contains all of them and may cause memory limitation problems.

    @param chunks: iterator of list of strings
    @param sep: split separator
    @param filter: function that returns a parsed result from each entry.
                    if returns None, False or empty string, the entry will be ignored)     
    """
    overflow = ''

    for chunk in chunks:
        idx = 0
        next_idx = chunk.find(sep) # find first separator

        #print 'chunk:"' + chunk.replace('\n', '\\n') + '"'

        # if next separator in chunk, split it !
        while next_idx != -1:
            # call given filter function on substring between current and next separators 
            next_val = filter(overflow + chunk[idx:next_idx])

            #print '    next:', next_idx, 'index:', idx, 'overflow:"' + overflow + '" val:"' + overflow + chunk[idx:next_idx] + '"', 'chunk:"' + chunk[next_idx+1:].replace('\n', '\\n') + '"'

            # reset overflow
            overflow = ''

            # if filter return a non empty string, return it 
            if next_val:
                yield next_val

            # shift current index and find the next one 
            idx = next_idx + 1
            next_idx = chunk.find(sep, idx)

        # if no separator (index = 0) append the entire chunk to overflow. 
        # Else overflow is the remaining string after last separator
        overflow = overflow + chunk if idx == 0 else chunk[idx:]

    # this line handle case of last entry without separator at end of chunks
    next_val = filter(overflow) if overflow else ''

    if next_val:
        yield next_val


def iter_as_chunk(iterable, step):
    """Iterator that returns chunks from an iterable.
    @param chunks: iterator
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
    """ Iterator that returns chunks from an iterable using slices (usefull for requests)
    @param chunks: iterator
    @param step: chunks size
    """
    index = 0

    while index != -1:
        chunk = iterable[index:index + step]
        chunk_length = len(chunk)

        index = index + step if chunk_length == step else -1

        if chunk_length:
            yield chunk
