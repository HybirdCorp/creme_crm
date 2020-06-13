# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2020  Hybird
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
from django.forms.fields import CharField
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.forms.bulk import BulkDefaultEditForm
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import EntityFilter


class ReportFilterBulkForm(BulkDefaultEditForm):
    def __init__(self, model, field, user, entities, is_bulk=False, **kwargs):
        super().__init__(model, field, user, entities, is_bulk=is_bulk, **kwargs)

        filter_field = self.fields['field_value']
        filter_field.empty_label = _('All')

        first_ct = entities[0].ct if entities else None
        self._has_same_report_ct = all(e.ct == first_ct for e in entities)
        self._uneditable_ids = set()

        if self._has_same_report_ct:
            user = self.user
            # filter_field.queryset = EntityFilter.get_for_user(user, first_ct)
            filter_field.queryset = EntityFilter.objects.filter_by_user(user)\
                                                        .filter(entity_type=first_ct)

            self._uneditable_ids = uneditable_ids = {
                e.id
                for e in entities
                if e.filter and not e.filter.can_view(user)[0]
            }

            if uneditable_ids:
                length = len(uneditable_ids)

                if length == len(entities):
                    self.fields['field_value'] = CharField(
                        label=filter_field.label,
                        required=False, widget=Label,
                        initial=ngettext(
                            'The filter cannot be changed because it is private.',
                            'The filters cannot be changed because they are private.',
                            length
                        ),
                    )
                else:
                    self.fields['beware'] = CharField(
                        label=_('Beware !'),
                        required=False, widget=Label,
                        initial=ngettext(
                            'The filter of {count} report cannot be changed because it is private.',
                            'The filters of {count} reports cannot be changed because they are private.',
                            length
                        ).format(count=length),
                    )
        else:
            filter_field.help_text = _(
                'Filter field can only be updated when '
                'reports target the same type of entities (e.g: only contacts).'
            )
            filter_field.widget = Label(empty_label='')
            filter_field.value = None

    def clean(self):
        if not self._has_same_report_ct:
            # TODO: error_messages
            raise ValidationError(
                _(
                    'Filter field can only be updated when reports '
                    'target the same type of entities (e.g: only contacts).'
                ),
                code='different_ctypes',
            )

        return super().clean()

    def _bulk_clean_entity(self, entity, values):
        if entity.id in self._uneditable_ids:
            raise ValidationError(
                _('The filter cannot be changed because it is private.'),
                code='private',
            )

        return super()._bulk_clean_entity(entity, values)
