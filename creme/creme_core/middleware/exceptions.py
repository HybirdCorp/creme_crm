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

import logging
from typing import Optional, Type

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin
from django.utils.encoding import smart_str  # smart_text

from creme.creme_core.core import exceptions as creme_exceptions
from creme.creme_core.http import is_ajax

logger = logging.getLogger(__name__)


class _AlternativeErrorMiddleware(MiddlewareMixin):
    error: Optional[Type[Exception]] = None
    status = 400
    template: Optional[str] = None
    # log_ajax = False
    log_ajax = True

    def process_exception(self, request, exception):
        if self.error is None or isinstance(exception, self.error):
            # msg = smart_text(exception)
            msg = smart_str(exception)

            # if request.is_ajax():
            if is_ajax(request):
                if self.log_ajax:
                    logger.exception('Error (status=%s)', self.status)

                return HttpResponse(msg, status=self.status)

            if self.template is None:
                return

            return render(
                request, self.template,
                {'error_message': msg}, status=self.status,
            )


class BadRequestMiddleware(_AlternativeErrorMiddleware):
    error = creme_exceptions.BadRequestError
    template = '400.html'


class Ajax403Middleware(_AlternativeErrorMiddleware):
    error = PermissionDenied
    status = 403


class Ajax404Middleware(_AlternativeErrorMiddleware):
    error = Http404
    status = 404


class Beautiful409Middleware(_AlternativeErrorMiddleware):
    error = creme_exceptions.ConflictError
    status = 409
    template = 'creme_core/conflict_error.html'


class Ajax500Middleware(_AlternativeErrorMiddleware):
    status = 500
    # log_ajax = True
