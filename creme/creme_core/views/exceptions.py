# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.utils.encoding import smart_str  # smart_text
from django.views.decorators.csrf import requires_csrf_token


@requires_csrf_token
def permission_denied(request, exception, template_name='creme_core/forbidden.html'):
    return HttpResponseForbidden(render_to_string(
        template_name,
        # {'error_message': smart_text(exception)},
        {'error_message': smart_str(exception)},
        request=request,
    ))
