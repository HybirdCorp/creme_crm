################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from django.template import Library

from creme.creme_core.models import CremeUser, EntityFilter

register = Library()


@register.filter
def efilter_view_forbidden(efilter: EntityFilter, user: CremeUser) -> str:
    """Return a translated error message if a user cannot view an EntityFilter
    An empty string means the user is allowed to view it.
    """
    # TODO: is the boolean really useful?
    allowed, msg = efilter.can_view(user)
    return '' if allowed else msg

# TODO: complete (edition, deletion)
