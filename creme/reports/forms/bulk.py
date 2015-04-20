# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2015  Hybird
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
from django.utils.translation import ugettext as _, ungettext

from creme.creme_core.forms.bulk import BulkDefaultEditForm
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import EntityFilter


class ReportFilterBulkForm(BulkDefaultEditForm):
    def __init__(self, field, user, entities, is_bulk=False, **kwargs):
        super(ReportFilterBulkForm, self).__init__(field, user, entities, is_bulk=is_bulk, **kwargs)

        filter_field = self.fields['field_value']
        filter_field.empty_label = _(u'All')

        first_ct = entities[0].ct if entities else None
        self._has_same_report_ct = all(e.ct == first_ct for e in entities)
        self._uneditable_ids = set()

        if self._has_same_report_ct:
            user = self.user
            filter_field.queryset = EntityFilter.get_for_user(user, first_ct)

            self._uneditable_ids = uneditable_ids = {e.id for e in entities
                                                        if e.filter and not e.filter.can_view(user)[0]
                                                    }

            if uneditable_ids:
                length = len(uneditable_ids)

                if length == len(entities):
                    self.fields['field_value'] = CharField(label=filter_field.label,
                                                           required=False, widget=Label,
                                                           initial=ungettext('The filter cannot be changed because it is private.',
                                                                             'The filters cannot be changed because they are private.',
                                                                             length
                                                                            ),
                                                          )
                else:
                    self.fields['beware'] = CharField(label=_('Beware !'),
                                                      required=False, widget=Label,
                                                      initial=ungettext('The filter of %s report cannot be changed because it is private.',
                                                                        'The filters of %s reports cannot be changed because they are private.',
                                                                        length
                                                                       ) % length,
                                                     )
        else:
            filter_field.help_text = _(u"Filter field can only be updated when "
                                       u"reports target the same type of entities (e.g: only contacts)."
                                      )
            filter_field.widget = Label(empty_label=u'')
            filter_field.value = None

    def clean(self):
        if not self._has_same_report_ct:
            # TODO: error_messages
            raise ValidationError(_(u"Filter field can only be updated when reports "
                                    u"target the same type of entities (e.g: only contacts)."
                                   ),
                                  code='different_ctypes',
                                 )

        return super(ReportFilterBulkForm, self).clean()

    def _bulk_clean_entity(self, entity, values):
        if entity.id in self._uneditable_ids:
            raise ValidationError(_('The filter cannot be changed because it is private.'),
                                  code='private',
                                 )

        #efilter = values.get('filter')

        #if efilter and entity.ct != efilter.entity_type:
            #raise ValidationError(_(u'Select a valid choice. That choice is not one of the available choices.'))

        return super(ReportFilterBulkForm, self)._bulk_clean_entity(entity, values)
