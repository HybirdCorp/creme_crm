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

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup

from ..forms.signature import SignatureForm
from ..models import EmailSignature


@login_required
@permission_required('emails')
def add(request):
    return add_model_with_popup(request, SignatureForm,
                                title=EmailSignature.creation_label,
                                submit_label=EmailSignature.save_label,
                               )


@login_required
@permission_required('emails')
def edit(request, signature_id):
    return edit_model_with_popup(request, {'pk': signature_id},
                                 model=EmailSignature, form_class=SignatureForm,
                                 can_change=EmailSignature.can_change_or_delete,
                                )


@login_required
@permission_required('emails')
def delete(request):
    signature = get_object_or_404(EmailSignature, pk=get_from_POST_or_404(request.POST, 'id'))

    if not signature.can_change_or_delete(request.user):
        raise PermissionDenied(_(u'You can not delete this signature (not yours)'))

    signature.delete()

    if request.is_ajax():
        # return HttpResponse(content_type='text/javascript')
        return HttpResponse()

    return HttpResponseRedirect('/')
