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

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_entity, edit_entity, list_view

from billing.models import CreditNote
from billing.forms.credit_note import CreditNoteCreateForm, CreditNoteEditForm
from billing.views.base import view_billing_entity


@login_required
@permission_required('billing')
@permission_required('billing.add_creditnote')
def add(request):
    return add_entity(request, CreditNoteCreateForm)

def edit(request, credit_note_id):
    return edit_entity(request, credit_note_id, CreditNote, CreditNoteEditForm, 'billing')

@login_required
@permission_required('billing')
def detailview(request, credit_note_id):
    credit_note = get_object_or_404(CreditNote, pk=credit_note_id)
    return view_billing_entity(request, credit_note, '/billing/credit_note')

@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, CreditNote, extra_dict={'add_url': '/billing/credit_note/add'})
