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

from django.db.models import ForeignKey
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CREME_REPLACE, Relation

from .. import get_template_base_model
from ..constants import REL_SUB_CREDIT_NOTE_APPLIED
from .base import Base
from .other_models import CreditNoteStatus


class AbstractCreditNote(Base):
    status = ForeignKey(
        CreditNoteStatus,
        verbose_name=_('Status of credit note'), on_delete=CREME_REPLACE,
    )

    creation_label = _('Create a credit note')
    save_label     = _('Save the credit note')

    class Meta(Base.Meta):
        abstract = True
        verbose_name = _('Credit note')
        verbose_name_plural = _('Credit notes')

    def get_absolute_url(self):
        return reverse('billing__view_cnote', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('billing__create_cnote')

    def get_edit_absolute_url(self):
        return reverse('billing__edit_cnote', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('billing__list_cnotes')

    # TODO: factorise the build() methods
    def build(self, template):
        # Specific recurrent generation rules
        status_id = 1  # Default status (see populate.py)

        if isinstance(template, get_template_base_model()):
            tpl_status_id = template.status_id

            if CreditNoteStatus.objects.filter(pk=tpl_status_id).exists():
                status_id = tpl_status_id

        self.status_id = status_id

        return super().build(template)

    def _update_linked_docs(self):
        # TODO: factorise (Relation.get_real_objects() ??)
        relations = Relation.objects.filter(
            subject_entity=self.id, type=REL_SUB_CREDIT_NOTE_APPLIED,
        ).select_related('object_entity')
        Relation.populate_real_object_entities(relations)

        for rel in relations:
            rel.object_entity.get_real_entity().save()

    def restore(self):
        super().restore()
        self._update_linked_docs()

    def trash(self):
        super().trash()
        self._update_linked_docs()


class CreditNote(AbstractCreditNote):
    class Meta(AbstractCreditNote.Meta):
        swappable = 'BILLING_CREDIT_NOTE_MODEL'
