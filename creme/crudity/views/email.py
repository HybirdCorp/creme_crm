# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from unicodedata import normalize

from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.conf import settings
from django.template.context import RequestContext
from django.template.loader import render_to_string

from persons.models.contact import Contact

from crudity.backends.models import CrudityBackend
from crudity.registry import crudity_registry


@login_required
@permission_required('crudity')
def download_email_template(request, subject):
    subject = CrudityBackend.normalize_subject(subject)
    backend = None

    input = crudity_registry.get_fetcher('email').get_input('raw', 'create')
    if input is not None:
        backend = input.get_backend(subject)

    if backend is None:
        raise Http404(u"This backend is not registered")

    try:
        contact_user = Contact.objects.get(is_user=request.user)
    except Contact.DoesNotExist:
        raise Http404(u"You have no contact file")

    response = HttpResponse(render_to_string("crudity/create_email_template.html",
                                             {'backend': backend,
                                              'contact': contact_user,
                                              'to':      settings.CREME_GET_EMAIL
                                             },
                                             context_instance=RequestContext(request)
                                            ),
                            mimetype="application/vnd.sealed.eml"
                           )
    response['Content-Disposition'] = 'attachment; filename=%s.eml' % \
                                        normalize('NFKD', unicode(CrudityBackend.normalize_subject(backend.subject))).encode('ascii', 'ignore')
    return response
