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

# import warnings
from django.db.models import ForeignKey
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CREME_REPLACE, Relation

# from .. import get_template_base_model
from ..constants import REL_SUB_CREDIT_NOTE_APPLIED
from .base import Base
from .other_models import CreditNoteStatus, get_default_credit_note_status_pk


class AbstractCreditNote(Base):
    status = ForeignKey(
        CreditNoteStatus,
        verbose_name=_('Status of credit note'),
        on_delete=CREME_REPLACE,
        default=get_default_credit_note_status_pk,
    )

    creation_label = _('Create a credit note')
    save_label     = _('Save the credit note')

    generate_number_in_create = False

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

    # def build(self, template):
    #     warnings.warn(
    #         'The method billing.models.Invoice.build() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     status = None
    #
    #     if isinstance(template, get_template_base_model()):
    #         status = CreditNoteStatus.objects.filter(uuid=template.status_uuid).first()
    #
    #     self.status = status or CreditNoteStatus.objects.default()
    #
    #     return super().build(template)

    def _update_linked_docs(self):
        for rel in Relation.objects.filter(
            subject_entity=self.id, type=REL_SUB_CREDIT_NOTE_APPLIED,
        ).prefetch_related('real_object'):
            rel.real_object.save()

    def restore(self):
        super().restore()
        self._update_linked_docs()

    def trash(self):
        super().trash()
        self._update_linked_docs()


class CreditNote(AbstractCreditNote):
    class Meta(AbstractCreditNote.Meta):
        swappable = 'BILLING_CREDIT_NOTE_MODEL'
