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

from django.http import HttpResponseServerError
from django.template import Context, loader #RequestContext
from django.conf import settings


#def page_not_found(request, template_name='404.html'):
    #"""404 handler."""
    #t = loader.get_template(template_name)
    #return http.HttpResponseNotFound(t.render(RequestContext(request, {'request_path': request.path})))

def server_error(request, template_name='500.html'):
    """500 error handler."""
    t = loader.get_template(template_name)
    return HttpResponseServerError(t.render(Context({'MEDIA_URL': settings.MEDIA_URL})))
