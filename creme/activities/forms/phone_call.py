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

from activities.models import PhoneCall, PhoneCallType
from activity import ActivityCreateForm, RelatedActivityCreateForm


def _init_fields(fields):
    fields['call_type'].initial = 2 #TODO: use constant

    now = datetime.now().replace(microsecond=0, second=0)
    fields['start_time'].initial = now.time()
    fields['end_time'].initial   = (now + timedelta(minutes=5)).time()


class RelatedPhoneCallCreateForm(RelatedActivityCreateForm):
    class Meta(RelatedActivityCreateForm.Meta):
        model = PhoneCall
        exclude = RelatedActivityCreateForm.Meta.exclude + ('type', )


    def __init__(self, *args, **kwargs):
        super(RelatedPhoneCallCreateForm, self).__init__(*args, **kwargs)

        if not self.instance.id: #TODO: useful (create -> instance not created ??!!)
            _init_fields(self.fields)


class PhoneCallCreateWithoutRelationForm(ActivityCreateForm):
    class Meta(ActivityCreateForm.Meta):
        model = PhoneCall
        exclude = ActivityCreateForm.Meta.exclude + ('type',)

    def __init__(self, *args, **kwargs):
        super(PhoneCallCreateWithoutRelationForm, self).__init__(*args, **kwargs)

        _init_fields(self.fields)
