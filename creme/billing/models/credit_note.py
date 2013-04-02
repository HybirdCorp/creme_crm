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

from django.db.models import ForeignKey, PROTECT
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import Relation

from creme.billing.constants import REL_SUB_CREDIT_NOTE_APPLIED
from base import Base
from other_models import CreditNoteStatus


class CreditNote(Base):
    status = ForeignKey(CreditNoteStatus, verbose_name=_(u"Status of credit note"), on_delete=PROTECT)

    #research_fields = Base.research_fields + ['status__name']
    #excluded_fields_in_html_output = Base.excluded_fields_in_html_output + ['base_ptr']
    #header_filter_exclude_fields = Base.header_filter_exclude_fields + ['base_ptr'] #todo: use a set() ??
    creation_label = _('Add a credit note')

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Credit note')
        verbose_name_plural = _(u'Credit notes')

    def get_absolute_url(self):
        return "/billing/credit_note/%s" % self.id

    def get_edit_absolute_url(self):
        return "/billing/credit_note/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/billing/credit_note"

    def build(self, template):
        # Specific recurrent generation rules
        self.status = CreditNoteStatus.objects.get(pk = template.status_id)
        return super(CreditNote, self).build(template)

    def _update_linked_docs(self):
        #TODO: factorise (Relation.get_real_objects() ??)
        relations = Relation.objects.filter(subject_entity=self.id,
                                            type=REL_SUB_CREDIT_NOTE_APPLIED,
                                           ) \
                                    .select_related('object_entity')
        Relation.populate_real_object_entities(relations)

        for rel in relations:
            rel.object_entity.get_real_entity().save()

    def restore(self):
        super(CreditNote, self).restore()
        self._update_linked_docs()

    def trash(self):
        super(CreditNote, self).trash()
        self._update_linked_docs()
