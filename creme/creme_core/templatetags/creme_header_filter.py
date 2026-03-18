################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.template import Library

from ..core.exceptions import ConflictError

if TYPE_CHECKING:
    from ..models import CremeUser, HeaderFilter

register = Library()


@register.filter
def hfilter_edition_forbidden(hfilter: HeaderFilter, user: CremeUser) -> str:
    try:
        hfilter.check_edition(user=user)
    except (PermissionDenied, ConflictError) as e:
        return str(e)

    return ''


@register.filter
def hfilter_deletion_forbidden(hfilter: HeaderFilter, user: CremeUser) -> str:
    try:
        hfilter.check_deletion(user=user)
    except (PermissionDenied, ConflictError) as e:
        return str(e)

    return ''

# TODO: hfilter_view_forbidden
