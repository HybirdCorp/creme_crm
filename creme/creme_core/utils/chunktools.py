################################################################################
#
# Copyright (c) 2009-2025 Hybird
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
# FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
################################################################################

from collections.abc import Callable, Iterable, Iterator
from typing import Literal, TypeVar

T = TypeVar('T')


# TODO: need a type "Boolable" for 'parser'
def iter_splitchunks(chunks: Iterable[str],
                     sep: str,
                     parser: Callable[[str], str | Literal[False] | None] | None = None,
                     limit: int | None = None,
                     ) -> Iterator[str]:
    """Iterator through chunks as split single stream.

    @param chunks: iterable of strings.
    @param sep: split separator.
    @param parser: function that returns a parsed result from each entry.
           if returns None, False or empty string, the entry will be ignored.
    @param limit: single line length limit. Throws a ValueError if reached.
    """
    overflow = ''

    for chunk in chunks:
        lines = (overflow + chunk).split(sep)
        overflow = lines[-1]

        if limit is not None and len(lines[0]) > limit:
            raise ValueError(f'line length is over {limit} characters')

        entries = map(parser, lines[:-1]) if parser is not None else lines[:-1]

        for entry in entries:
            if entry:
                yield entry

    last = parser(overflow) if parser is not None else overflow

    if last:
        yield last


def iter_as_chunk(iterable: Iterable[T], step: int) -> Iterator[list[T]]:
    """Iterator which returns chunks from an iterable.
    @param iterable: iterator.
    @param step: chunks size.
    """
    chunk: list[T] = []

    for index, item in enumerate(iterable):
        if not index % step and chunk:
            yield chunk
            chunk = []

        chunk.append(item)

    if chunk:
        yield chunk


def iter_as_slices(iterable, step):
    """Iterator that returns chunks from an iterable using slices.
    @param iterable: iterator.
    @param step: chunks size.
    """
    index = 0

    while index != -1:
        chunk = iterable[index:index + step]
        chunk_length = len(chunk)

        index = index + step if chunk_length == step else -1

        if chunk_length:
            yield chunk
