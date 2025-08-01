################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme import billing
from creme.creme_core.models import Relation
from creme.creme_core.views import generic
from creme.creme_core.views.decorators import _check_required_model_fields

from .. import constants, custom_forms
from ..forms import credit_note as cnote_forms
from . import base

CreditNote = billing.get_credit_note_model()


class CreditNoteCreation(generic.EntityCreation):
    model = CreditNote
    form_class = custom_forms.CNOTE_CREATION_CFORM


class CreditNoteDetail(generic.EntityDetail):
    model = CreditNote
    template_name = 'billing/view_credit_note.html'
    pk_url_kwarg = 'cnote_id'


class CreditNoteEdition(generic.EntityEdition):
    model = CreditNote
    form_class = custom_forms.CNOTE_EDITION_CFORM
    pk_url_kwarg = 'cnote_id'


class CommentEdition(generic.EntityEditionPopup):
    model = CreditNote
    form_class = cnote_forms.CreditNotePopupEditionForm
    pk_url_kwarg = 'cnote_id'

    def check_view_permissions(self, user):
        _check_required_model_fields(CreditNote, 'comment')
        super().check_view_permissions(user)


class CreditNotesLinking(generic.RelatedToEntityFormPopup):
    form_class = cnote_forms.CreditNotesRelatedForm
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


class CreditNoteRemoving(generic.CremeModelDeletion):
    model = Relation
    permissions = 'billing'

    def check_instance_permissions(self, instance, user):
        has_perm = user.has_perm_to_unlink_or_die
        has_perm(instance.subject_entity)
        has_perm(instance.object_entity)

    def get_query_kwargs(self):
        return {
            'subject_entity': self.kwargs['base_id'],
            'object_entity': self.kwargs['credit_note_id'],
            'type': constants.REL_OBJ_CREDIT_NOTE_APPLIED,
        }

    def get_success_url(self):
        # TODO: callback_url?
        return self.object.subject_entity.get_absolute_url()


class CreditNotesList(base.BaseList):
    model = CreditNote
    default_headerfilter_id = constants.DEFAULT_HFILTER_CNOTE
