################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2020  Hybird
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

from functools import partial

from django.contrib.auth import decorators as original_decorators
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

# Alias in order the user to only import this module (& not the django one)
login_required = original_decorators.login_required

# TODO: raise our own exception in order to set a better message ?
permission_required = partial(original_decorators.permission_required, raise_exception=True)


def _check_superuser(user):
    if user.is_superuser:
        return True

    raise PermissionDenied(_('You are not super-user.'))


superuser_required = original_decorators.user_passes_test(_check_superuser)
