################################################################################
#
# Copyright (c) 2023 Hybird
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

from django.core import paginator


class OnePagePaginator(paginator.Paginator):
    """Specialisation of paginator made to manage only one page.
    - It uses the same API as Paginator.
    - If the content is small enough to be contained by the first (& only) page,
      the COUNT query is not performed.
    So it's useful to get a truncated/limited number of instances AND get the
    total count in the same time.
    """
    def __init__(self, object_list, per_page, *args, **kwargs):
        # TODO: assert QuerySet?
        super().__init__(object_list=object_list, per_page=per_page)

        limited_list = object_list[0:per_page]
        length = len(limited_list)
        # TODO: work with list too?
        self._count = length if length < per_page else object_list.count()
        self._unique_page = self._get_page(limited_list, 1, self)

    @property
    def count(self):
        return self._count

    def page(self, number):
        # TODO: copy?
        return self._unique_page

    @property
    def page_range(self):
        return range(1, 2)
