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

# import warnings
from collections import Counter
from collections.abc import Iterable
from typing import Iterator

from django.conf import settings
from django.db.models import Model
from django.utils.translation import gettext

from creme.creme_core.models import utils

if settings.USE_I18N:
    from django.utils.translation import _trans

    def plural(number: int) -> bool:
        return bool(_trans.translation(_trans.get_language()).plural(number))
else:
    def plural(number: int) -> bool:
        return number != 1

# Simple Django version
# def get_model_verbose_name(model: type[Model], count: int):
#     return model._meta.verbose_name_plural if plural(count) else model._meta.verbose_name

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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


def smart_model_verbose_name(model: type[Model], count: int) -> str:
    """Get the verbose name or the plural verbose name of a model depending on a count."""
    return (
        utils.model_verbose_name_plural(model)
        if plural(count) else
        utils.model_verbose_name(model)
    )


# def get_model_verbose_name(model, count):
#     warnings.warn(
#         'The function creme_core.utils.translation.get_model_verbose_name() is deprecated; '
#         'use smart_model_verbose_name() instead.',
#         DeprecationWarning
#     )
#
#     return smart_model_verbose_name(model=model, count=count)


def verbose_instances_groups(instances: Iterable[Model]) -> Iterator[str]:
    """Generates labels describing groups of instances.

    Example:
        >> for label in verbose_instances_groups([my_contact1, my_organisation, my_contact2]):
        >>     print(label)
        "2 Contacts"
        "1 Organisation"
    """
    counter = Counter(type(instance) for instance in instances)

    if counter:
        fmt = gettext('{count} {model}').format

        for model, count in counter.items():
            yield fmt(
                count=count,
                model=smart_model_verbose_name(model=model, count=count),
            )
