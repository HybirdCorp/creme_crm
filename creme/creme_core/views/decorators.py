# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2018  Hybird
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

from functools import wraps

from django.http import Http404
from django.utils.translation import ugettext as _

from ..core.exceptions import ConflictError
from ..models import FieldsConfig


def POST_only(view):
    @wraps(view)
    def POST_view(request, *args, **kwargs):
        if request.method != 'POST':
            raise Http404('This method uses POST method.')

        return view(request, *args, **kwargs)

    return POST_view


def _check_required_model_fields(model, *field_names):
    is_hidden = FieldsConfig.get_4_model(model).is_fieldname_hidden

    for field_name in field_names:
        if is_hidden(field_name):
            raise ConflictError(_('The field "{model}.{field}" is hidden.').format(
                model=model.__name__,
                field=field_name,
            ))


def require_model_fields(model, *field_names):
    def _decorator(view):
        @wraps(view)
        def _aux(*args, **kwargs):
            _check_required_model_fields(model, *field_names)

            return view(*args, **kwargs)

        return _aux

    return _decorator
