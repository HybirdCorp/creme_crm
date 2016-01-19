# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import Relation
from creme.creme_core.views.decorators import require_model_fields
from creme.creme_core.views.generic import (add_entity, edit_entity, list_view,
        view_entity, add_to_entity, edit_model_with_popup)

from .. import get_credit_note_model
from ..constants import REL_OBJ_CREDIT_NOTE_APPLIED, DEFAULT_HFILTER_CNOTE
from ..forms.credit_note import (CreditNoteCreateForm,
        CreditNoteEditForm, CreditNotePopupEditForm, CreditNoteRelatedForm)


CreditNote = get_credit_note_model()


def abstract_add_credit_note(request, form=CreditNoteCreateForm,
                             initial_status=1,
                             submit_label=_('Save the credit note'),
                            ):
    return add_entity(request, form, extra_initial={'status': initial_status},
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_link_to_credit_notes(request, base_id, form=CreditNoteRelatedForm,
                                  title=_(u'Credit notes for «%s»'),
                                  submit_label=_('Save the credit notes')
                                 ):
    return add_to_entity(request, base_id, form, title, link_perm=True,
                         submit_label=submit_label,
                        )


def abstract_edit_credit_note(request, credit_note_id, form=CreditNoteEditForm):
    return edit_entity(request, credit_note_id, CreditNote, form)


@require_model_fields(CreditNote, 'comment')
def abstract_edit_cnote_comment(request, credit_note_id, form=CreditNotePopupEditForm):
    return edit_model_with_popup(request, {'pk': credit_note_id}, CreditNote, form)


def abstract_view_creditnote(request, credit_note_id, template='billing/view_billing.html'):
    return view_entity(request, credit_note_id, CreditNote,
                       template=template,
                       extra_template_dict={'can_download': True},
                      )


@login_required
@permission_required(('billing', cperm(CreditNote)))
def add(request):
    return abstract_add_credit_note(request)


@login_required
@permission_required('billing')
def link_to_credit_notes(request, base_id):
    return abstract_link_to_credit_notes(request, base_id)


@login_required
@permission_required('billing')
def edit(request, credit_note_id):
    return abstract_edit_credit_note(request, credit_note_id)


@login_required
@permission_required('billing')
def edit_comment(request, credit_note_id):
    return abstract_edit_cnote_comment(request, credit_note_id)


@login_required
@permission_required('billing')
def detailview(request, credit_note_id):
    return abstract_view_creditnote(request, credit_note_id)


@login_required
@permission_required('billing')
def listview(request):
    return list_view(request, CreditNote, hf_pk=DEFAULT_HFILTER_CNOTE)


@login_required
@permission_required('billing')
def delete_related_credit_note(request, credit_note_id, base_id):
    relation = get_object_or_404(Relation, subject_entity=base_id,
                                 object_entity=credit_note_id,
                                 type=REL_OBJ_CREDIT_NOTE_APPLIED,
                                )
    subject = relation.subject_entity

    has_perm = request.user.has_perm_to_unlink_or_die
    has_perm(subject)
    has_perm(relation.object_entity)

    relation.get_real_entity().delete()

    return redirect(subject.get_real_entity())
