# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2019  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.fields import OptionalModelChoiceField

from ..models import Calendar


class UserParticipationField(OptionalModelChoiceField):
    # def __init__(self, user=None, sub_label=_(u'Appears on the calendar:'), *args, **kwargs):
    def __init__(self, *, user=None, sub_label=_('Appears on the calendar:'), **kwargs):
        super().__init__(sub_label=sub_label,
                         queryset=Calendar.objects.none(),
                         # *args, **kwargs
                         **kwargs
                        )
        self.user = user

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user

        if user is not None:
            calendars_field = self.fields[1]
            calendars_field.queryset = Calendar.objects.filter(user=user)

            self.widget.sub_widget.choices = calendars_field.choices
