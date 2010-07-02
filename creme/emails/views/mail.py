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

from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response

from creme_core.entities_access.functions_for_permissions import read_object_or_die
from creme_core.views.generic.popup import inner_popup

from emails.blocks import mails_history_block
from emails.models.mail import Email



@login_required
def reload_block_mails_history(request, entity_id):
    return mails_history_block.detailview_ajax(request, entity_id)

@login_required
def view_mail(request, mail_id):
    email = get_object_or_404(Email, pk=mail_id)
    die_status = read_object_or_die(request, email)

    if die_status:
        return die_status

    template = "emails/view_email.html"
    ctx_dict = {'mail': email, 'title':  'Détails du mail'}
    if request.is_ajax():
        return inner_popup(request, template,
                           ctx_dict,
                           is_valid=False,
                           reload=False,
                           context_instance=RequestContext(request))

    return render_to_response(template, ctx_dict,
                              context_instance=RequestContext(request))