# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014  Hybird
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

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext

from creme.creme_core.forms.bulk import BulkDefaultEditForm
from creme.creme_core.forms.widgets import Label


class ReportFilterBulkForm(BulkDefaultEditForm):
    def __init__(self, model, field_name=None, user=None, entities=(), is_bulk=False, **kwargs):
        super(ReportFilterBulkForm, self).__init__(model, field_name=field_name, user=user, entities=entities, is_bulk=is_bulk, **kwargs)

        filter_field = self.fields['field_value']
        filter_field.empty_label = ugettext(u'All')

        first_ct = entities[0].ct if entities else None
        self._has_same_report_ct = all(e.ct == first_ct for e in entities)

        if self._has_same_report_ct:
            filter_field.queryset = filter_field.queryset.filter(entity_type=first_ct)
        else:
            filter_field.help_text = ugettext(u"Filter field can only be updated when reports target the same type of entities (e.g: only contacts).")
            filter_field.widget = Label(empty_label=u'')
            filter_field.value = None

    def clean(self):
        if not self._has_same_report_ct:
            raise ValidationError(ugettext(u"Filter field can only be updated when reports target the same type of entities (e.g: only contacts)."))

        return super(ReportFilterBulkForm, self).clean()

    def _bulk_clean_entity(self, entity, **values):
        filter = values.get('filter')

        if filter and entity.ct != filter.entity_type:
            raise ValidationError(ugettext(u'Select a valid choice. That choice is not one of the available choices.'))

        return super(ReportFilterBulkForm, self)._bulk_clean_entity(entity, **values)
