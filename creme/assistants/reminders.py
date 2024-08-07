################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from datetime import timedelta

from django.conf import settings
from django.db.models import Q
# from django.utils.translation import gettext as _
from django.utils.timezone import localtime, now

from creme.creme_core.core.reminder import Reminder
from creme.creme_core.models import SettingValue

from .models import Alert, ToDo
from .notification import AlertReminderContent, TodoReminderContent
from .setting_keys import todo_reminder_key

# TODO: in settings.py? SettingValue (do not  forget to refresh job on update)? Job's data?
TODO_REMINDER_DAYS_BEFORE = 1


class AssistantReminder(Reminder):
    def get_users(self, instance):
        return [instance.user or instance.entity.user]


class ReminderAlert(AssistantReminder):
    id = Reminder.generate_id('assistants', 'alert')
    model = Alert

    def _get_delta(self):
        return timedelta(minutes=getattr(settings, 'DEFAULT_TIME_ALERT_REMIND', 30))

    def get_notification_content(self, instance):
        return AlertReminderContent(instance)

    def get_Q_filter(self):
        return Q(
            trigger_date__lte=now() + self._get_delta(),
            is_validated=False,
        )

    def next_wakeup(self, now_value):
        alert = Alert.objects.filter(
            is_validated=False, reminded=False, trigger_date__isnull=False,
        ).order_by('trigger_date').first()

        return alert.trigger_date - self._get_delta() if alert is not None else None


class ReminderTodo(AssistantReminder):
    id = Reminder.generate_id('assistants', 'todo')
    model = ToDo

    def _get_delta(self):
        return timedelta(days=TODO_REMINDER_DAYS_BEFORE)

    def _get_min_hour(self):
        return SettingValue.objects.get_4_key(key=todo_reminder_key, default=9).value

    def get_notification_content(self, instance):
        return TodoReminderContent(instance)

    def get_Q_filter(self):
        # TODO: exclude Todos related to deleted entities?
        return Q(deadline__lte=now() + self._get_delta(), is_ok=False)

    def ok_for_continue(self):
        return localtime(now()).hour >= self._get_min_hour()

    def next_wakeup(self, now_value):
        wakeup = None
        todo = ToDo.objects.filter(
            is_ok=False, reminded=False, deadline__isnull=False,
        ).order_by('deadline').first()

        if todo is not None:
            wakeup = localtime(todo.deadline - self._get_delta())
            min_hour = self._get_min_hour()

            if wakeup.hour < min_hour:
                if wakeup < now_value:
                    wakeup = localtime(now_value)

                wakeup = wakeup.replace(hour=min_hour)

        return wakeup
