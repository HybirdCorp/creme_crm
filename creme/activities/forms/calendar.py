# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.forms import ModelChoiceField
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

from creme.creme_core.forms.base import CremeModelForm

from ..models import Calendar


class CalendarForm(CremeModelForm):
    class Meta:
        model = Calendar
        exclude = ('user',)

    def get_user(self):
        return self.user

    def save(self):
        self.instance.user = self.get_user()
        return super(CalendarForm, self).save()


class CalendarConfigForm(CalendarForm):
    def __init__(self, *args, **kwargs):
        super(CalendarForm, self).__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['user'] = ModelChoiceField(label=_('User'),
                                                   queryset=User.objects.all(),
                                                   empty_label=None,
                                                   initial=self.user.id,
                                                  )

    def get_user(self):
        return self.cleaned_data.get('user') or self.instance.user
