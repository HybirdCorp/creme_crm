################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2025  Hybird
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

from django.utils.decorators import method_decorator
from django.views.generic.base import View

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.core.exceptions import ConflictError


class ErrorView(View):
    error_class: type[Exception] = ConflictError
    message: str = 'These view has been disabled'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        raise self.error_class(self.message)
