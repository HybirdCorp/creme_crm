################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2017-2025 Hybird
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
from dataclasses import dataclass

from django import forms
from django.contrib.auth import get_user_model
from django.forms import widgets
from django.utils.translation import gettext_lazy as _

import creme.creme_core.forms.fields as core_fields
import creme.creme_core.forms.widgets as core_widgets
from creme.creme_config.forms.fields import CreatorEnumerableModelChoiceField
from creme.creme_core.forms import validators
from creme.creme_core.forms.enumerable import NO_LIMIT
from creme.persons import get_contact_model

from .. import get_activity_model
from ..models import Calendar


class ActivitySubTypeField(CreatorEnumerableModelChoiceField):
    def __init__(self, *,
                 model=get_activity_model(), field_name='sub_type',
                 limit_choices_to=None,
                 **kwargs):
        super().__init__(model, field_name, **kwargs)
        self.limit_choices_to = limit_choices_to
        # Bypass limits here to prevent usage of "more" feature that does not
        # support the "limit_choice_to" yet
        self.limit = NO_LIMIT

    @property
    def limit_choices_to(self):
        return self.enum.enumerator.limit_choices_to

    @limit_choices_to.setter
    def limit_choices_to(self, limit_choices_to):
        """
        limit_choices_to can be a Q object or a dictionary of keyword lookup
        arguments.
        """
        self.enum.enumerator.limit_choices_to = limit_choices_to

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        result.limit_choices_to = self.limit_choices_to
        return result

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['data-selection-show-group'] = 'true'
        return attrs


class DateWithOptionalTimeWidget(widgets.MultiWidget):
    template_name = 'activities/forms/widgets/datetime.html'

    def __init__(self, attrs=None):
        super().__init__(
            widgets=(core_widgets.CalendarWidget, core_widgets.TimeWidget),
            attrs=attrs,
        )

    def decompress(self, value):
        return (value[0], value[1]) if value else (None, None)


class DateWithOptionalTimeField(forms.MultiValueField):
    widget = DateWithOptionalTimeWidget

    @dataclass(frozen=True)
    class DateWithOptionalTime:
        date: datetime.date
        time: datetime.time | None = None

    def __init__(self, *, required=True, **kwargs):
        super().__init__(
            fields=(
                forms.DateField(required=required),
                forms.TimeField(required=False),
            ),
            require_all_fields=False,
            required=required,
            **kwargs
        )

    def compress(self, data_list):
        return self.DateWithOptionalTime(
            date=data_list[0], time=data_list[1],
        ) if data_list else None


class UserParticipationField(core_fields.OptionalModelChoiceField):
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
            if user.linked_contact:
                calendars_field = self.fields[1]
                calendars_field.queryset = Calendar.objects.filter(user=user)

                self.widget.sub_widget.choices = calendars_field.choices
            else:
                # TODO: we should be able to reset the widget if user is changed again...
                self.widget = core_widgets.Label(
                    empty_label=_('You cannot participate as staff user'),
                )

    def clean(self, value):
        user = self._user
        assert user is not None

        if not user.linked_contact:
            return self.Option(is_set=False, data=None)

        return super().clean(value=value)

    def validate(self, value):
        super().validate(value=value)

        user = self._user
        assert user is not None
        validators.validate_linkable_entity(user.linked_contact, user)


class ParticipatingUsersField(forms.ModelMultipleChoiceField):
    def __init__(self, *,
                 user=None,
                 queryset=get_user_model().objects.filter(is_staff=False),
                 **kwargs):
        super().__init__(queryset=queryset, **kwargs)
        self.user = user

    def clean(self, value):
        user = self.user
        assert user is not None

        contact_users = set()
        teams = set()

        for part_user in super().clean(value=value):
            if part_user.is_team:
                contact_users.update(part_user.teammates.values())
                teams.add(part_user)
            else:
                contact_users.add(part_user)

        return {
            'contacts': [
                *validators.validate_linkable_entities(
                    entities=get_contact_model().objects
                                                .filter(is_user__in=contact_users)
                                                .select_related('is_user'),
                    user=self.user,
                ),
            ],
            'calendars': [
                *Calendar.objects.get_default_calendars(contact_users | teams).values(),
            ],
        }
