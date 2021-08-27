# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

# import warnings
from functools import partial

from django.db.models.query import Q
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import base
from creme.creme_core.forms.fields import MultiCreatorEntityField
from creme.creme_core.models import Relation

# from .base import BaseCreateForm, BaseEditForm
from .. import constants, get_credit_note_model

CreditNote = get_credit_note_model()


# class CreditNoteCreateForm(BaseCreateForm):
#     class Meta(BaseCreateForm.Meta):
#         model = CreditNote
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('CreditNoteCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


# class CreditNoteEditForm(BaseEditForm):
#     class Meta(BaseEditForm.Meta):
#         model = CreditNote
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('CreditNoteEditForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)


class CreditNotePopupEditForm(base.CremeModelForm):
    class Meta:
        model = CreditNote
        fields = ('comment',)


# class CreditNoteRelatedForm(base.CremeForm):
class CreditNotesRelatedForm(base.CremeForm):
    credit_notes = MultiCreatorEntityField(label=_('Credit notes'), model=CreditNote)

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.billing_document = entity
        existing = Relation.objects.filter(
            subject_entity=entity.id, type=constants.REL_OBJ_CREDIT_NOTE_APPLIED,
        )

        # TODO: waiting for automated change of status when a credit note is out
        #       of date by looking to expiration date
        # TODO: Add another filter today <= expiration_date ??
        q_filter = (
            ~Q(pk__in=[rel.object_entity_id for rel in existing])
            & Q(
                currency=entity.currency.id,
                # TODO: workflow status
                relations__type=constants.REL_SUB_BILL_RECEIVED,
                relations__object_entity=entity.get_real_entity().target.id,
            )
        )

        self.fields['credit_notes'].q_filter = q_filter

    def save(self):
        create_relation = partial(
            Relation.objects.safe_create,
            subject_entity=self.billing_document,
            type_id=constants.REL_OBJ_CREDIT_NOTE_APPLIED,
            user=self.user,
        )

        for entity in self.cleaned_data['credit_notes']:
            create_relation(object_entity=entity)
