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

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import Relation
from creme_core.views.generic import add_entity, edit_entity, list_view, view_entity, add_to_entity, edit_model_with_popup

from billing.models import CreditNote
from billing.forms.credit_note import CreditNoteCreateForm, CreditNoteEditForm, CreditNotePopupEditForm, CreditNoteRelatedForm
from billing.constants import REL_OBJ_CREDIT_NOTE_APPLIED


@login_required
@permission_required('billing')
@permission_required('billing.add_creditnote')
def add(request):
    return add_entity(request, CreditNoteCreateForm, extra_initial={'status': 1})

@login_required
@permission_required('billing')
def edit(request, credit_note_id):
    return edit_entity(request, credit_note_id, CreditNote, CreditNoteEditForm)

@login_required
@permission_required('billing')
def edit_comment(request, credit_note_id):
    return edit_model_with_popup(request, {'pk': credit_note_id},
                                 CreditNote, CreditNotePopupEditForm,
                                 can_change=CreditNote.can_change)

@login_required
@permission_required('billing')
def detailview(request, credit_note_id):
    return view_entity(request, credit_note_id, CreditNote,
                       '/billing/credit_note', 'billing/view_billing.html',
                       {'can_download': True},
                      )

@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, CreditNote, extra_dict={'add_url': '/billing/credit_note/add'})

@login_required
@permission_required('billing')
def add_related_credit_note(request, base_id):
    return add_to_entity(request, base_id, CreditNoteRelatedForm, _(u"Credit notes for <%s>"), link_perm=True)

@login_required
@permission_required('billing')
def delete_related_credit_note(request, credit_note_id, base_id):
    relation = get_object_or_404(Relation, subject_entity=base_id, object_entity=credit_note_id, type=REL_OBJ_CREDIT_NOTE_APPLIED)
    subject  = relation.subject_entity
    user = request.user

    subject.can_unlink_or_die(user)
    relation.object_entity.can_unlink_or_die(user)

    relation.get_real_entity().delete()

    return HttpResponseRedirect(subject.get_real_entity().get_absolute_url())
