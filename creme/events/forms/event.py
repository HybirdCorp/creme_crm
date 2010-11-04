# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.forms import DateTimeField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import Relation
from creme_core.forms import CremeEntityForm, CremeForm, RelatedEntitiesField
from creme_core.forms.widgets import DateTimeWidget

from events.models import Event
from events.constants import *


class EventForm(CremeEntityForm):
    start_date = DateTimeField(label=_(u'Start date'), widget=DateTimeWidget)
    end_date   = DateTimeField(label=_(u'End date'), required=False, widget=DateTimeWidget)

    class Meta(CremeEntityForm.Meta):
        model = Event


class AddContactsToEventForm(CremeForm):
    related_contacts = RelatedEntitiesField(relation_types=[REL_OBJ_IS_INVITED_TO, REL_OBJ_CAME_EVENT, REL_OBJ_NOT_CAME_EVENT],
                                            label=_(u'Related contacts'))

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('instance')
        super(AddContactsToEventForm, self).__init__(*args, **kwargs)

    def save(self):
        event = self.event
        create_relation = Relation.create

        for relationtype_id, contact in self.cleaned_data['related_contacts']:
            create_relation(event, relationtype_id, contact)

