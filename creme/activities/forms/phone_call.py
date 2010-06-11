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

from django.utils.translation import ugettext as _

from datetime import datetime, timedelta, time 

from django.forms.models import ModelChoiceField
from django.forms import BooleanField, DateTimeField, TimeField

from creme_core.forms.widgets import CalendarWidget, TimeWidget

from assistants.models.alert import Alert

from activities.models import PhoneCall, ActivityType, PhoneCallType
from activities.constants import ACTIVITYTYPE_PHONECALL
from activity import ActivityCreateForm, ActivityEditForm


class PhoneCallCreateForm(ActivityCreateForm):
    class Meta(ActivityCreateForm.Meta):
        model = PhoneCall

    type           = ModelChoiceField(empty_label=None, queryset=ActivityType.objects.filter(pk=ACTIVITYTYPE_PHONECALL))
    generate_alert = BooleanField(label=_(u"Voulez vous générer une alerte ou un rappel ?"), required=False)
    alert_day      = DateTimeField(label=_(u"Jour de l'alerte"), widget=CalendarWidget(), required=False)
    start_time     = TimeField(label=_(u"Heure de l'alerte"), widget=TimeWidget(), required=False)

    blocks = ActivityCreateForm.blocks.new(
                ('alert_datetime', _(u'Générer une alerte ou un rappel'), ['generate_alert', 'alert_day', 'start_time']),
                )


    def __init__(self, *args, **kwargs):
        super(PhoneCallCreateForm, self).__init__(*args, **kwargs)

        fields = self.fields
        fields['type'].initial = ActivityType.objects.get(pk=ACTIVITYTYPE_PHONECALL)

        if not self.instance.id: #TODO: useful (create -> instance not created ??!!)
            fields['call_type'].initial = PhoneCallType.objects.get(id=2) #TODO: use constant

            now = datetime.now().replace(microsecond=0, second=0)
            fields['start_time'].initial = now.time()
            fields['end_time'].initial = (now + timedelta(minutes=5)).time()
 
    def save(self):
        cleaned_data = self.cleaned_data

        cleaned_data['type'] = ActivityType.objects.get(pk=ACTIVITYTYPE_PHONECALL)
        super(PhoneCallCreateForm, self).save()

        if cleaned_data['generate_alert']:
            alert_time = cleaned_data.get('start_time', time())

            trigger_date = cleaned_data['alert_day'].replace(hour=alert_time.hour, minute=alert_time.minute)
            alert = Alert(for_user=self.instance.user, trigger_date=trigger_date)
            alert.creme_entity = self.instance
            alert.title ='Alerte en rapport avec appel téléphonique'
            alert.description ='Alerte en rapport avec appel téléphonique'
            alert.save()


class PhoneCallEditForm(ActivityEditForm):
    class Meta(ActivityEditForm.Meta):
        model = PhoneCall
