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
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _

from crudity.backends.registry import from_email_crud_registry
from crudity.backends.email.create.base import drop_from_email_backend
from crudity.fetchers.pop import pop_frontend

def _fetch_emails(user):
    message_count, emails = pop_frontend.fetch(delete=True)
    create_be = from_email_crud_registry.get_creates()
    default_be = create_be.get("*", drop_from_email_backend)

    for email in emails:
        subject = email.subject.replace(' ', '').upper()
        backend = create_be.get(subject)
        if not backend:
            backend = default_be

        backend.create(email, user)
    return message_count

@login_required
@permission_required('crudity')
def fetch_emails(request, template="crudity/waiting_actions.html", ajax_template="crudity/frags/ajax/waiting_actions.html", extra_tpl_ctx=None, extra_req_ctx=None):
    context = RequestContext(request)

    if extra_req_ctx:
        context.update(extra_req_ctx)

    create_be = from_email_crud_registry.get_creates()

    message_count = _fetch_emails(request.user)

    blocks = []
    blocks_append = blocks.append

    ct_get_for_model = ContentType.objects.get_for_model
    for name, backend in create_be.items():
        model    = backend.model
        be_type  = backend.type

        if be_type and model:
            for be_block in backend.blocks:
                blocks_append(be_block(ct_get_for_model(model), be_type, backend.get_buttons()).detailview_display(context))

    tpl_dict = {'blocks': blocks, 'frontend_verbose': _(u"Emails"), 'messages_count': message_count, 'backends': create_be.items()}

    if extra_tpl_ctx:
        tpl_dict.update(extra_tpl_ctx)

    if request.is_ajax():
        return HttpResponse(render_to_string(ajax_template, tpl_dict, context_instance=context))

    return render_to_response(template, tpl_dict, context_instance=context)
