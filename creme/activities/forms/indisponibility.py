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

import datetime

from django.forms.util import ValidationError
from django.forms import IntegerField, DateTimeField, TimeField
from django.utils.translation import ugettext as _

from creme_core.forms import CremeEntityForm
from creme_core.forms.widgets import DateTimeWidget

from activities.models import Activity, ActivityType
from activities.constants import ACTIVITYTYPE_INDISPO
from activity import ActivityCreateForm


class IndisponibilityCreateForm(CremeEntityForm):
    class Meta(CremeEntityForm.Meta):
        model = Activity
        exclude = CremeEntityForm.Meta.exclude + ('type',)

    start = DateTimeField(label=_(u'Début'), widget=DateTimeWidget())
    end   = DateTimeField(label=_(u'Fin'), widget=DateTimeWidget())

    blocks = CremeEntityForm.blocks.new(
                ('datetime', _(u'Quand'), ['start', 'end', 'is_all_day']),
            )

    def __init__(self, *args, **kwargs):
        super(IndisponibilityCreateForm, self).__init__(*args, **kwargs)

        fields = self.fields
        now = datetime.datetime.now()
        fields['start'].initial = now.replace(hour=9, minute=0, second=0, microsecond=0)
        fields['end'].initial   = now.replace(hour=18, minute=0, second=0, microsecond=0)

    def clean(self):
        cleaned_data = self.cleaned_data

        if self._errors:
            return cleaned_data

        if cleaned_data.get('start') > cleaned_data.get('end'):
            raise ValidationError(_(u"L'heure de fin est avant le début"))

        return cleaned_data

    def save(self):
        self.instance.type = ActivityType.objects.get(pk=ACTIVITYTYPE_INDISPO)
        super(IndisponibilityCreateForm, self).save()
