# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.template import RequestContext
from django.template.loader import render_to_string


class Beautiful403Middleware(object):
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            return HttpResponseForbidden(render_to_string('creme_core/forbidden.html',
                                                          RequestContext(request, {'error_message': unicode(exception)})))
