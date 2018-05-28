# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

# import warnings

from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode
from django.views.decorators.csrf import requires_csrf_token


# def server_error(request, template_name='500.html'):
#     "500 error handler."
#     warnings.warn('creme.creme_core.views.exceptions.server_error() is deprecated ; '
#                   'use django.views.defaults.server_error() instead.',
#                   DeprecationWarning
#                  )
#     from django.http import HttpResponseServerError
#
#     return HttpResponseServerError(render_to_string(template_name, request=request))


@requires_csrf_token
def permission_denied(request, exception, template_name='creme_core/forbidden.html'):
    protected_objects = None
    args = exception.args

    if len(args) > 1:
        msg = smart_unicode(args[0])
        arg = args[1]

        if isinstance(arg, dict):
            protected_objects = arg.get('protected_objects')
    else:
        msg = smart_unicode(exception)

    return HttpResponseForbidden(render_to_string(template_name,
                                                  {'error_message':     msg,
                                                   'protected_objects': protected_objects,
                                                  },
                                                  request=request,
                                                 )
                                )
