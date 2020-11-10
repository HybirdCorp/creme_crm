# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2020  Hybird
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

from django.contrib.auth import get_user_model
from django.forms import ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import validators
from creme.creme_core.forms.fields import OptionalModelChoiceField
from creme.persons import get_contact_model

from ..models import Calendar


class UserParticipationField(OptionalModelChoiceField):
    def __init__(self, *, user=None, sub_label=_('Appears on the calendar:'), **kwargs):
        super().__init__(
            sub_label=sub_label,
            queryset=Calendar.objects.none(),
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

    def clean(self, value):
        user = self._user
        assert user is not None

        value = super().clean(value=value)
        validators.validate_linkable_entity(user.linked_contact, user)

        return value


class ParticipatingUsersField(ModelMultipleChoiceField):
    def __init__(self, *,
                 user=None,
                 queryset=get_user_model().objects.filter(is_staff=False),
                 **kwargs):
        super().__init__(queryset=queryset, **kwargs)
        self.user = user

    def clean(self, value):
        user = self.user
        assert user is not None

        users = set()

        for part_user in super().clean(value=value):
            if not part_user.is_team:
                users.add(part_user)
            else:
                users.update(part_user.teammates.values())

        return validators.validate_linkable_entities(
            get_contact_model().objects.filter(is_user__in=users).select_related('is_user'),
            self.user,
        )
