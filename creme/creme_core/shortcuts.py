################################################################################
#
# Copyright (c) 2019-2025 Hybird
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

from django.http import Http404
from django.shortcuts import _get_queryset


def get_bulk_or_404(klass,
                    id_list: list | None = None,
                    *,
                    field_name: str = 'pk') -> dict:
    """Returns a dictionary of objects for a given list of IDs.

    (see the method .in_bulk() of QuerySet)

    @param klass: May be a Model, Manager, or QuerySet object.
    @param id_list: List of IDs (optional). If <None>, all instances are retrieved.
    @param field_name: Name of the field to use as ID (optional & "pk" by default) ;
           Beware, the field must be "unique=True".
    @raise Http404: If at least one instance is missing.
    """

    queryset = _get_queryset(klass)

    if not hasattr(queryset, 'filter'):
        name = klass.__name__ if isinstance(klass, type) else klass.__class__.__name__
        raise ValueError(
            f"First argument to get_bulk_or_404() must be a Model, Manager, "
            f"or QuerySet, not '{name}'."
        )

    bulk = queryset.in_bulk(id_list, field_name=field_name)

    if id_list is not None:
        id_set = {str(i) for i in id_list}

        if len(bulk) != len(id_set):
            bulk_ids = {str(k) for k in bulk}

            raise Http404('These IDs cannot be found: {}'.format(
                ', '.join(i for i in id_set if i not in bulk_ids)
            ))

    return bulk
