# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.shortcuts import render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode

from creme.creme_core.core.exceptions import ConflictError


class Beautiful403Middleware(object):
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            protected_objects = None
            args = exception.args

            if len(args) > 1:
                msg = smart_unicode(args[0])
                arg = args[1]

                if isinstance(arg, dict):
                    protected_objects = arg.get('protected_objects')
            else:
                msg = smart_unicode(exception)

            if request.is_ajax(): #TODO: use protected_objects ??
                return HttpResponse(msg, mimetype='text/javascript', status=403)

            return HttpResponseForbidden(render_to_string('creme_core/forbidden.html',
                                                          RequestContext(request,
                                                                         {'error_message':     msg,
                                                                          'protected_objects': protected_objects,
                                                                         },
                                                                        )
                                                         )
                                        )


class _AlternativeErrorMiddleware(object):
    error = None
    template = None

    def process_exception(self, request, exception):
        if self.error is None or isinstance(exception, self.error):
            msg = smart_unicode(exception)

            if request.is_ajax():
                return HttpResponse(msg, mimetype='text/javascript', status=self.status)

            if self.template is None:
                return

            return render(request, self.template,
                          {'error_message': msg}, status=self.status,
                         )


class Ajax404Middleware(_AlternativeErrorMiddleware):
    error = Http404
    status = 404


class Beautiful409Middleware(_AlternativeErrorMiddleware):
    error = ConflictError
    status = 409
    template = 'creme_core/conflict_error.html'


class Ajax500Middleware(_AlternativeErrorMiddleware):
    status = 500

