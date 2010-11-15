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
from django.contrib.auth.models import User

from creme_core.forms.base import CremeModelForm

from activities.models.activity import Calendar

class _CalendarForm(CremeModelForm):
    class Meta:
        model = Calendar
        exclude = ('id', 'is_custom')

    def save(self):
        instance = self.instance
        instance.is_custom = True

        if instance.is_default:
            Calendar.objects.filter(user=self.cleaned_data['user']).update(is_default=False)

        super(_CalendarForm, self).save()
        return instance


class CalendarForm(_CalendarForm):

    def __init__(self, user=None, *args, **kwargs):
        super(CalendarForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['user'].queryset = User.objects.filter(pk=user.pk)
            self.fields['user'].initial  = user.pk
            self.fields['user'].empty_label  = None

    def save(self):
        super(CalendarForm, self).save()


class CalendarConfigForm(_CalendarForm):

    def __init__(self, *args, **kwargs):
        super(CalendarConfigForm, self).__init__(*args, **kwargs)

    def save(self):
        super(CalendarConfigForm, self).save()
