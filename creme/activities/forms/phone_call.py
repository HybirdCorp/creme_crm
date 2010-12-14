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

from datetime import datetime, timedelta, time

from django.forms import BooleanField
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.forms import CremeDateTimeField, CremeTimeField

from assistants.models.alert import Alert

from activities.models import PhoneCall, PhoneCallType
from activity import RelatedActivityCreateForm, ActivityCreateForm


def _init_fields(fields):
    fields['call_type'].initial = 2 #TODO: use constant

    now = datetime.now().replace(microsecond=0, second=0)
    fields['start_time'].initial = now.time()
    fields['end_time'].initial   = (now + timedelta(minutes=5)).time()

def _generate_alert(phone_call, cleaned_data):
    if cleaned_data['generate_alert']:
        alert_start_time = cleaned_data.get('alert_start_time') or time()
        alert_day        = cleaned_data.get('alert_day') or phone_call.start

        #TODO: use Alert.objects.create() ??
        alert = Alert()
        alert.for_user     = phone_call.user
        alert.trigger_date = alert_day.replace(hour=alert_start_time.hour, minute=alert_start_time.minute)
        alert.creme_entity = phone_call
        alert.title        = ugettext(u"Alert of phone call")
        alert.description  = ugettext(u'Alert related to a phone call')
        alert.save()


class RelatedPhoneCallCreateForm(RelatedActivityCreateForm):
    generate_alert   = BooleanField(label=_(u"Do you want to generate an alert or a reminder ?"), required=False)
    alert_day        = CremeDateTimeField(label=_(u"Alert day"), required=False)
    alert_start_time = CremeTimeField(label=_(u"Alert time"), required=False)

    class Meta(RelatedActivityCreateForm.Meta):
        model = PhoneCall
        exclude = RelatedActivityCreateForm.Meta.exclude + ('type', )

    blocks = RelatedActivityCreateForm.blocks.new(
                    ('alert_datetime', _(u'Generate an alert or a reminder'), ['generate_alert', 'alert_day', 'alert_start_time']),
                )

    def __init__(self, *args, **kwargs):
        super(RelatedPhoneCallCreateForm, self).__init__(*args, **kwargs)

        if not self.instance.id: #TODO: useful (create -> instance not created ??!!)
            _init_fields(self.fields)

    def save(self):
        instance = super(RelatedPhoneCallCreateForm, self).save()
        _generate_alert(instance, self.cleaned_data)

        return instance


#TODO: use multiple inheritage to factorise alert code ???
class PhoneCallCreateForm(ActivityCreateForm):
    generate_alert   = BooleanField(label=_(u"Do you want to generate an alert or a reminder ?"), required=False)
    alert_day        = CremeDateTimeField(label=_(u"Alert day"), required=False)
    alert_start_time = CremeTimeField(label=_(u"Alert time"), required=False)

    class Meta(ActivityCreateForm.Meta):
        model = PhoneCall
        exclude = ActivityCreateForm.Meta.exclude + ('type',)

    blocks = ActivityCreateForm.blocks.new(
                    ('alert_datetime', _(u'Generate an alert or a reminder'), ['generate_alert', 'alert_day', 'alert_start_time']),
                )

    def __init__(self, *args, **kwargs):
        super(PhoneCallCreateForm, self).__init__(*args, **kwargs)

        _init_fields(self.fields)

    def save(self):
        instance = super(PhoneCallCreateForm, self).save()
        _generate_alert(instance, self.cleaned_data)

        return instance
