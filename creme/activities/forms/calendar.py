################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

# import warnings
# from django.contrib.auth import get_user_model
from django.db.transaction import atomic
from django.forms import ModelChoiceField
from django.utils.translation import gettext_lazy as _

import creme.creme_config.forms.generics as gen_forms
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import base

from .. import get_activity_model
from ..models import Calendar

Activity = get_activity_model()


# class CalendarForm(base.CremeModelForm):
#     class Meta:
#         model = Calendar
#         exclude = ('user',)
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         warnings.warn('CalendarForm is deprecated.', DeprecationWarning)
#
#     def get_user(self):
#         return self.user
#
#     def save(self, *args, **kwargs):
#         self.instance.user = self.get_user()
#         return super().save(*args, **kwargs)


class MyCalendarForm(base.CremeModelForm):
    class Meta:
        model = Calendar
        exclude = ('user',)

    def __init__(self, user, *args, **kwargs):
        super().__init__(user=user, *args, **kwargs)
        self.instance.user = user


# class CalendarConfigForm(CalendarForm):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         warnings.warn(
#             'CalendarConfigForm is deprecated; '
#             'use CalendarConfigCreationForm/CalendarConfigEditionForm instead.',
#             DeprecationWarning,
#         )
#
#         if not self.instance.pk:
#             self.fields['user'] = ModelChoiceField(
#                 label=_('User'),
#                 queryset=get_user_model().objects
#                                          .filter(is_staff=False)
#                                          .exclude(is_team=True, calendar__isnull=False),
#                 empty_label=None,
#                 initial=self.user.id,
#             )
#
#     def get_user(self):
#         return self.cleaned_data.get('user') or self.instance.user


class CalendarConfigCreationForm(base.CremeModelForm):
    class Meta:
        model = Calendar
        exclude = ()


class CalendarConfigEditionForm(base.CremeModelForm):
    class Meta:
        model = Calendar
        exclude = ('user',)


class CalendarM2MReplacer(gen_forms.M2MHandler):
    def _build_formfield_queryset(self):
        instance = self.instance_to_delete

        return Calendar.objects.filter(user=instance.user).exclude(id=instance.id)

    def _get_choicefield_data(self):
        data = super()._get_choicefield_data()
        data['help_text'] = _(
            'The activities on the deleted calendar will be moved to the selected one.'
        )

        return data


class CalendarDeletionForm(gen_forms.DeletionForm):
    def _get_m2m_handler_class(self, model_field):
        remote_field = model_field.remote_field
        if remote_field.model == Activity and remote_field.name == 'calendars':
            return CalendarM2MReplacer

        return super()._get_m2m_hanlder_class(model_field)


# TODO: manage multi-calendar better
class ActivityCalendarLinkerForm(base.CremeForm):
    calendar = ModelChoiceField(label=_('Calendar'), queryset=None, empty_label=None)

    def __init__(self, instance, *args, **kwargs):
        self.activity = instance
        super().__init__(*args, **kwargs)
        user = self.user
        calendars = instance.calendars.filter(user=user)[:2]

        if len(calendars) > 1:
            raise ConflictError(
                "You can change the calendar only when there "
                "is only one calendar related to the activity"
            )

        self.calendar = calendar = calendars[0]

        calendar_field = self.fields['calendar']
        calendar_field.queryset = Calendar.objects.filter(user=user)
        calendar_field.initial = calendar.id

    def save(self, *args, **kwargs):
        old_calendar = self.calendar
        new_calendar = self.cleaned_data.get('calendar')

        if new_calendar != old_calendar:
            calendars = self.activity.calendars

            with atomic():
                calendars.remove(old_calendar)
                calendars.add(new_calendar)
