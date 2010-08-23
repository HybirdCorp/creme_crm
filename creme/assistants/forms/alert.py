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

from datetime import datetime, time

from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeModelWithUserForm, CremeDateTimeField, CremeTimeField

from assistants.models import Alert


class AlertEditForm(CremeModelWithUserForm):
    trigger_date = CremeDateTimeField(label=_(u"Trigger date")) #Date d'échéance
    trigger_time = CremeTimeField(label=_(u'Hour'), required=False)

    class Meta:
        model = Alert
        exclude = ('entity_content_type', 'is_validated', 'entity_id', 'for_user')

    def __init__(self, entity, *args, **kwargs):
        super(AlertEditForm, self).__init__(*args, **kwargs)
        self.entity = entity
        self.fields['trigger_time'].initial = self.instance.trigger_date.time() if self.instance.trigger_date else time()

    def clean(self):
        if self._errors:
            return self.cleaned_data

        cleaned_data = self.cleaned_data

        trigger_date = cleaned_data.get("trigger_date")
        trigger_time = cleaned_data.get('trigger_time', time())
        cleaned_data["trigger_date"] = trigger_date.replace(hour=trigger_time.hour, minute=trigger_time.minute)

        return cleaned_data

    def save (self):
        entity = self.entity

        instance = self.instance
        instance.entity_content_type = entity.entity_type
        instance.entity_id = entity.id
        instance.for_user = self.cleaned_data['user'] 

        super(AlertEditForm, self).save()


class AlertCreateForm(AlertEditForm): #useful ??
    def save (self):
        super(AlertCreateForm, self).save()
