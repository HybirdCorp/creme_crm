################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023-2025  Hybird
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

from datetime import time

from django import forms
from django.core.exceptions import ValidationError
from django.utils.formats import date_format
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.activities.models import CalendarConfigItem, Weekday
from creme.creme_core.forms import CremeModelForm, FieldBlockManager
from creme.creme_core.models import UserRole


class BaseCalendarConfigItemForm(CremeModelForm):
    week_days = forms.MultipleChoiceField(
        label=_('Days of the week'), choices=Weekday, required=True,
    )

    class Meta:
        model = CalendarConfigItem
        exclude = ('role', 'week_days', 'extra_data')

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['week_days'].initial = self.instance.week_days

    def clean_week_days(self):
        return [int(d) for d in self.cleaned_data.get('week_days', ())]

    def clean(self, *args, **kwargs):
        cleaned_data = self.cleaned_data

        day_start = cleaned_data.get('day_start')
        day_end = cleaned_data.get('day_end')

        if day_start and day_end and day_start >= day_end:
            raise ValidationError(
                gettext('Day start ({start}) must be before end ({end}).').format(
                    start=date_format(day_start, 'TIME_FORMAT'),
                    end=date_format(day_end, 'TIME_FORMAT'),
                )
            )

        view_day_start = cleaned_data.get('view_day_start')
        view_day_end = cleaned_data.get('view_day_end')
        view_day_all = (view_day_start == view_day_end) and (view_day_start == time(0, 0, 0))

        if view_day_all:
            return cleaned_data

        if view_day_start >= view_day_end:
            raise ValidationError(
                gettext('Visible start ({start}) must be before end ({end}).').format(
                    start=date_format(view_day_start, 'TIME_FORMAT'),
                    end=date_format(view_day_end, 'TIME_FORMAT'),
                )
            )

        if view_day_start > day_start or view_day_end < day_end:
            raise ValidationError(
                gettext(
                    'The visible range of the day ({start} − {end}) should contains '
                    'the working hours ({day_start} − {day_end}) or some events will '
                    'not be displayed'
                ).format(
                    start=date_format(view_day_start, 'TIME_FORMAT'),
                    end=date_format(view_day_end, 'TIME_FORMAT'),
                    day_start=date_format(day_start, 'TIME_FORMAT'),
                    day_end=date_format(day_end, 'TIME_FORMAT'),
                )
            )

        return cleaned_data

    def save(self, *args, **kwargs):
        self.instance.week_days = self.cleaned_data['week_days']
        return super().save(*args, **kwargs)


class CalendarConfigItemCreateForm(BaseCalendarConfigItemForm):
    role = forms.ModelChoiceField(
        label=_('Role'),
        queryset=UserRole.objects.none(),
        empty_label=None, required=False,
    )

    blocks = FieldBlockManager(
        {
            'id': 'role',
            'label': _('Role'),
            'fields': ('role',),
        }, {
            'id': 'settings',
            'label': _('Settings'),
            'fields': '*',
        },
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        qs, empty_label = self.get_role_field_info()

        role_field = self.fields['role']
        role_field.queryset = qs
        role_field.empty_label = empty_label

    def get_role_field_info(self):
        empty_label = None
        existing_role_ids = set(
            CalendarConfigItem.objects.exclude(role__isnull=True, superuser=False)
                                      .values_list('role', flat=True)
        )

        try:
            existing_role_ids.remove(None)
        except KeyError:
            empty_label = '*{}*'.format(_('Superuser'))

        return UserRole.objects.exclude(pk__in=existing_role_ids), empty_label

    def save(self, *args, **kwargs):
        role = self.cleaned_data['role']
        instance = self.instance

        instance.role = role
        instance.superuser = (role is None)

        return super().save(*args, **kwargs)


class CalendarConfigItemEditForm(BaseCalendarConfigItemForm):
    blocks = FieldBlockManager(
        {
            'id': 'settings',
            'label': _('Settings'),
            'fields': ('*'),
        },
    )
