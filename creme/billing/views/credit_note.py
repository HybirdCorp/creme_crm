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

import warnings

from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import Relation
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import require_model_fields, _check_required_model_fields

from ... import billing

from .. import constants
from ..forms import credit_note as cnote_forms

from . import base

CreditNote = billing.get_credit_note_model()

# Function views --------------------------------------------------------------


def abstract_add_credit_note(request, form=cnote_forms.CreditNoteCreateForm,
                             initial_status=1,
                             submit_label=CreditNote.save_label,
                            ):
    warnings.warn('billing.views.credit_note.abstract_add_credit_note() is deprecated ; '
                  'use the class-based view CreditNoteCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_entity(request, form, extra_initial={'status': initial_status},
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_link_to_credit_notes(request, base_id, form=cnote_forms.CreditNoteRelatedForm,
                                  title=_('Credit notes for «%s»'),
                                  submit_label=_('Save the credit notes'),
                                 ):
    warnings.warn('billing.views.credit_note.abstract_link_to_credit_notes() is deprecated ; '
                  'use the class-based view CreditNotesLinking instead.',
                  DeprecationWarning
                 )
    return generic.add_to_entity(request, base_id, form, title, link_perm=True,
                                 submit_label=submit_label,
                                )


def abstract_edit_credit_note(request, credit_note_id, form=cnote_forms.CreditNoteEditForm):
    warnings.warn('billing.views.credit_note.abstract_edit_creditnote() is deprecated ; '
                  'use the class-based view CreditNoteEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, credit_note_id, CreditNote, form)


@require_model_fields(CreditNote, 'comment')
def abstract_edit_cnote_comment(request, credit_note_id, form=cnote_forms.CreditNotePopupEditForm):
    warnings.warn('billing.views.credit_note.abstract_edit_cnote_comment() is deprecated ; '
                  'use the class-based view CommentEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_model_with_popup(request, {'pk': credit_note_id}, CreditNote, form)


def abstract_view_creditnote(request, credit_note_id, template='billing/view_credit_note.html'):
    warnings.warn('billing.views.credit_note.abstract_view_creditnote() is deprecated ; '
                  'use the class-based view CreditNoteDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, credit_note_id, CreditNote, template=template)


@login_required
@permission_required(('billing', cperm(CreditNote)))
def add(request):
    warnings.warn('billing.views.credit_note.add() is deprecated', DeprecationWarning)
    return abstract_add_credit_note(request)


@login_required
@permission_required('billing')
def link_to_credit_notes(request, base_id):
    warnings.warn('billing.views.credit_note.link_to_credit_notes() is deprecated',
                  DeprecationWarning
                 )
    return abstract_link_to_credit_notes(request, base_id)


@login_required
@permission_required('billing')
def edit(request, credit_note_id):
    warnings.warn('billing.views.credit_note.edit() is deprecated', DeprecationWarning)
    return abstract_edit_credit_note(request, credit_note_id)


@login_required
@permission_required('billing')
def edit_comment(request, credit_note_id):
    warnings.warn('billing.views.credit_note.edit_comment() is deprecated', DeprecationWarning)
    return abstract_edit_cnote_comment(request, credit_note_id)


@login_required
@permission_required('billing')
def detailview(request, credit_note_id):
    warnings.warn('billing.views.credit_note.detailview() is deprecated', DeprecationWarning)
    return abstract_view_creditnote(request, credit_note_id)


@login_required
@permission_required('billing')
def listview(request):
    return generic.list_view(request, CreditNote, hf_pk=constants.DEFAULT_HFILTER_CNOTE)


@login_required
@permission_required('billing')
def delete_related_credit_note(request, credit_note_id, base_id):
    relation = get_object_or_404(Relation, subject_entity=base_id,
                                 object_entity=credit_note_id,
                                 type=constants.REL_OBJ_CREDIT_NOTE_APPLIED,
                                )
    subject = relation.subject_entity

    has_perm = request.user.has_perm_to_unlink_or_die
    has_perm(subject)
    has_perm(relation.object_entity)

    # relation.get_real_entity().delete()
    relation.delete()

    return redirect(subject.get_real_entity())


# Class-based views  ----------------------------------------------------------

class CreditNoteCreation(base.BaseCreation):
    model = CreditNote
    form_class = cnote_forms.CreditNoteCreateForm


class CreditNoteDetail(generic.EntityDetail):
    model = CreditNote
    template_name = 'billing/view_credit_note.html'
    pk_url_kwarg = 'cnote_id'


class CreditNoteEdition(generic.EntityEdition):
    model = CreditNote
    form_class = cnote_forms.CreditNoteEditForm
    pk_url_kwarg = 'cnote_id'


class CommentEdition(generic.EntityEditionPopup):
    model = CreditNote
    form_class = cnote_forms.CreditNotePopupEditForm
    pk_url_kwarg = 'cnote_id'

    def check_view_permissions(self, user):
        _check_required_model_fields(CreditNote, 'comment')
        super().check_view_permissions(user)


class CreditNotesLinking(generic.RelatedToEntityFormPopup):
    form_class = cnote_forms.CreditNoteRelatedForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    title = _('Credit notes for «{entity}»')
    submit_label = _('Link the credit notes')
    entity_id_url_kwarg = 'base_id'
    # TODO: factorise (see populate.py => REL_OBJ_CREDIT_NOTE_APPLIED)
    entity_classes = [
        billing.get_invoice_model(),
        billing.get_quote_model(),
        billing.get_sales_order_model(),
    ]

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)
