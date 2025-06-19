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

from collections.abc import Callable

from django.db.models import Model
from django.utils.translation import gettext

from ..utils import ellipsis
from .custom_entity import CustomEntityType


def assign_2_charfield(instance: Model,
                       field_name: str,
                       value: str,
                       truncate: Callable[[str, int], str] = ellipsis,
                       ) -> None:
    field = instance._meta.get_field(field_name)
    setattr(instance, field_name, truncate(value, field.max_length))


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


# TODO: accept ContentType?
def model_verbose_name(model: type[Model]) -> str:
    """Retrieve the verbose name of a model.
    Use it instead of <model._meta.verbose_name> for entity models, because it
    manages correctly custom entity types.
    """
    ce_type = CustomEntityType.objects.get_for_model(model)
    if ce_type is not None:
        if not ce_type.enabled:
            return gettext('Invalid custom type')

        if ce_type.deleted:
            return gettext('{custom_model} [deleted]').format(
                custom_model=ce_type.name,
            )

        return ce_type.name

    return str(model._meta.verbose_name)


# TODO: accept ContentType?
def model_verbose_name_plural(model: type[Model]) -> str:
    """Retrieve the plural verbose name of a model.
    Use it instead of <model._meta.verbose_name_plural> for entity models,
    because it manages correctly custom entity types.
    """
    ce_type = CustomEntityType.objects.get_for_model(model)
    if ce_type is not None:
        if not ce_type.enabled:
            return '?'

        if ce_type.deleted:
            return gettext('{custom_model} [deleted]').format(
                custom_model=ce_type.plural_name,
            )

        return ce_type.plural_name

    return str(model._meta.verbose_name_plural)
