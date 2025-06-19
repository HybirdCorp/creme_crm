################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023-2025  Hybird
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

from __future__ import annotations

from collections.abc import Iterable, Iterator
from enum import Enum, auto


class ViewTag(Enum):
    """Gives some context about what type rendering we want.
    HTML? we want some HTML tags in our render.
    Plain text? we do not want HTML tags.
    Is this a detail-view or a form?
    Etc...
    """

    HTML_DETAIL = auto()  # Detail-view
    HTML_LIST = auto()  # List-view
    # NB: list-view in inner-popup used as selector should be tagged as 'FORM'.
    HTML_FORM = auto()
    TEXT_PLAIN = auto()  # NB: used by CSV/XLS exporter

    @classmethod
    def smart_generator(cls, /, tags: ViewTag | Iterable[ViewTag] | str) -> Iterator[ViewTag]:
        """Helper for functions which takes several ViewTag as argument.
        @param tags: If it's an instance of ViewTag, this instance is yielded.
               If it's a sequences of ViewTags, these instances are yielded.
               If it's a string, the following values are accepted:
               "*" all tags are yielded
               "html*" all tags related to HTML are yielded.
               "text*" TEXT_PLAIN is yielded.
        """
        if isinstance(tags, cls):
            yield tags
        elif isinstance(tags, str):
            # TODO: use 'glob'?
            if tags == 'html*':
                yield cls.HTML_DETAIL
                yield cls.HTML_LIST
                yield cls.HTML_FORM
            elif tags == 'text*':
                yield cls.TEXT_PLAIN
            elif tags == '*':
                yield from cls
            else:
                raise ValueError(f'Invalid tag pattern {tags}')
        else:
            for tag in tags:
                if not isinstance(tag, cls):
                    raise TypeError(f'{tag} is not an instance of {cls}')

                yield tag
