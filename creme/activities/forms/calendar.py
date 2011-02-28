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

from creme_core.forms.base import CremeModelWithUserForm

from activities.models.activity import Calendar


class CalendarForm(CremeModelWithUserForm):
    class Meta:
        model = Calendar
        exclude = ('id', 'is_custom')

    def save(self):
        instance = self.instance
        instance.is_custom = True

        user = self.cleaned_data['user']

        if instance.is_default:
            Calendar.objects.filter(user=user).update(is_default=False)
            
        super(CalendarForm, self).save()

        if Calendar.objects.filter(user=user, is_default=True).count() == 0:
           instance.is_default = True
           instance.save()

        return instance
