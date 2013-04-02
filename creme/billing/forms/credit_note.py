# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from functools import partial

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms.fields import MultiCremeEntityField
from creme.creme_core.forms.validators import validate_linkable_entities
from creme.creme_core.forms.base import CremeModelForm, CremeForm
from creme.creme_core.models.relation import Relation

from ..constants import REL_SUB_BILL_RECEIVED, REL_OBJ_CREDIT_NOTE_APPLIED
from ..models import CreditNote
from .base import BaseCreateForm, BaseEditForm


class CreditNoteCreateForm(BaseCreateForm):
    class Meta(BaseCreateForm.Meta):
        model = CreditNote


class CreditNoteEditForm(BaseEditForm):
    class Meta(BaseEditForm.Meta):
        model = CreditNote


class CreditNotePopupEditForm(CremeModelForm):

    class Meta:
        model = CreditNote
        fields = ('comment',)


class CreditNoteRelatedForm(CremeForm):
    credit_notes = MultiCremeEntityField(label=_(u'Credit notes'), model=CreditNote)

    def __init__(self, entity, *args, **kwargs):
        super(CreditNoteRelatedForm, self).__init__(*args, **kwargs)
        self.billing_document = entity
        existing = Relation.objects.filter(subject_entity=entity.id, type=REL_OBJ_CREDIT_NOTE_APPLIED)

        # TODO waiting for automated change of status when a credit note is out of date by looking to expiration date
        # TODO Add another filter today <= expiration_date ??
        q_filter = {'~pk__in': [rel.object_entity_id for rel in existing],
                    'currency': entity.currency.id,
#                    'status': CreditNoteStatus.objects.get(pk=ISSUED_CREDIT_NOTE).id, # TODO workflow status
                    'relations__type' : REL_SUB_BILL_RECEIVED,
                    'relations__object_entity': entity.get_real_entity().get_target().id,
                   }

        self.fields['credit_notes'].q_filter = q_filter

    def clean_credit_notes(self):
        return validate_linkable_entities(self.cleaned_data['credit_notes'], self.user)

    def save(self):
        create_relation = partial(Relation.objects.create, subject_entity=self.billing_document,
                                  type_id=REL_OBJ_CREDIT_NOTE_APPLIED, user=self.user
                                 )

        for entity in self.cleaned_data['credit_notes']:
            create_relation(object_entity=entity)
