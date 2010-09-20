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

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _

from crudity.backends.registry import from_email_crud_registry
from crudity.backends.email.create.base import drop_from_email_backend
from crudity.blocks import WaitingActionBlock
from crudity.frontends.pop import pop_frontend


@login_required
def fetch_emails(request):
    context = RequestContext(request)
    message_count, emails = pop_frontend.fetch(delete=False)#TODO: Change to True when prod

    create_be = from_email_crud_registry.get_creates()

    default_be = create_be.get("*", drop_from_email_backend)

    for email in emails:
        subject = email.subject.replace(' ', '').upper()
        backend = create_be.get(subject)
        if not backend:
            backend = default_be

        backend.create(email)

    blocks = []

    ct_get_for_model = ContentType.objects.get_for_model
    for name, backend in create_be.items():
        model = backend.model
        type  = backend.type
        if backend.type and backend.model:
            blocks.append(WaitingActionBlock(ct_get_for_model(model), type).detailview_display(context))

    if request.is_ajax():
        return HttpResponse(render_to_string("crudity/frags/ajax/waiting_actions.html", {'blocks': blocks, 'frontend_verbose': _(u"Emails")}, context_instance=context))

    return render_to_response("crudity/waiting_actions.html", {'blocks': blocks, 'frontend_verbose': _(u"Emails")}, context_instance=context)
