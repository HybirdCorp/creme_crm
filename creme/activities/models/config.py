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

from django.db import models
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models.auth import UserRole
from creme.creme_core.models.base import CremeModel


class Weekday(models.IntegerChoices):
    MONDAY = 1, _('Monday')
    TUESDAY = 2, _('Tuesday')
    WEDNESDAY = 3, _('Wednesday')
    THURSDAY = 4, _('Thursday')
    FRIDAY = 5, _('Friday')
    SATURDAY = 6, _('Saturday')
    SUNDAY = 7, _('Sunday')

    @staticmethod
    def default_days():
        return (1, 2, 3, 4, 5, 6)


class CalendarViewMode(models.TextChoices):
    MONTH = 'month', _('Month')
    WEEK = 'week', _('Week')


class CalendarConfigItemManager(models.Manager):
    no_default_error_message = _('The default configuration for calendar is not populated.')

    def get_default(self):
        try:
            return CalendarConfigItem.objects.get(role__isnull=True, superuser=False)
        except CalendarConfigItem.DoesNotExist:
            raise ConflictError(str(self.no_default_error_message))

    def for_user(self, user):
        configs = {
            (c.role_id, c.superuser): c for c in (
                CalendarConfigItem.objects.filter(
                    models.Q(role=user.role, superuser=user.is_superuser)
                    | models.Q(role=None, superuser=False)
                )
            )
        }

        config = configs.get((user.role_id, user.is_superuser)) or configs.get((None, False))

        if config is None:
            raise ConflictError(str(self.no_default_error_message))

        return config


class CalendarConfigItem(CremeModel):
    """Stores configuration for Calendar UI"""
    role = models.ForeignKey(
        UserRole, null=True, default=None,
        on_delete=models.CASCADE, editable=False,
    )
    superuser = models.BooleanField(default=False, editable=False)

    view = models.CharField(
        verbose_name=_('Default view mode'),
        max_length=100,
        choices=CalendarViewMode,
        default='month',
    )

    view_day_start = models.TimeField(
        _('View start'), default=time(0, 0, 0), help_text=_(
            "Start of the displayed hours.\n"
            "Can be different from the day range that restricts the moves and creation of events"
        )
    )
    view_day_end = models.TimeField(
        _('View end'), default=time(0, 0, 0), help_text=_(
            'End of the displayed hours.\n'
            "Can be different from the day range that restricts the moves and creation of events"
        )
    )

    week_start = models.IntegerField(
        _('First day of the week'),
        choices=Weekday,
        default=Weekday.MONDAY.value
    )

    week_days = models.JSONField(
        _('Days of the week'), default=Weekday.default_days, editable=False
    ).set_tags(viewable=False)

    day_start = models.TimeField(_('Start'), default=time(8, 0, 0))
    day_end = models.TimeField(_('End'), default=time(18, 0, 0))

    slot_duration = models.TimeField(_('Slot duration'), default=time(0, 15, 0))

    allow_event_move = models.BooleanField(_('Allow drag-n-drop'), default=True)
    allow_keep_state = models.BooleanField(_('Keep navigation state'), default=False)

    # Can be used by third party code to store the data they want,
    # without having to modify the code.
    extra_data = models.JSONField(editable=False, default=dict).set_tags(viewable=False)

    objects = CalendarConfigItemManager()

    class Meta:
        app_label = 'activities'
        verbose_name = _('Calendar display configuration')
        verbose_name_plural = _('Calendar display configurations')

    @property
    def is_default(self):
        return not self.superuser and self.role is None

    @property
    def view_label(self):
        return CalendarViewMode(self.view).label

    @property
    def week_days_labels(self):
        return [Weekday(int(d)).label.title() for d in self.week_days]

    @property
    def week_start_label(self):
        return Weekday(self.week_start).label.title()

    def as_dict(self):
        if self.view_day_start != self.view_day_end:
            view_day_start = self.view_day_start.strftime('%H:%M')
            view_day_end = self.view_day_end.strftime('%H:%M')
        else:
            view_day_start = '00:00'
            view_day_end = '24:00'

        return {
            "view": self.view,
            "view_day_start": view_day_start,
            "view_day_end": view_day_end,
            "week_days": list(self.week_days),
            "week_start": self.week_start,
            "day_start": self.day_start.strftime('%H:%M'),
            "day_end": self.day_end.strftime('%H:%M'),
            "slot_duration": self.slot_duration.strftime('%H:%M:00'),
            "allow_event_move": self.allow_event_move,
            "allow_keep_state": self.allow_keep_state,
            "extra_data": self.extra_data,
        }
