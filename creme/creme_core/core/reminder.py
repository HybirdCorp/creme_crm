# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

import logging
# import warnings

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import gettext as _

from ..models import DateReminder, JobResult

logger = logging.getLogger(__name__)
FIRST_REMINDER = 1


class Reminder:
    id    = None  # Overload with an unicode object ; use generate_id()
    model = None  # Overload with a CremeModel

    def __init__(self):
        pass

    @staticmethod
    def generate_id(app_name, name):
        return 'reminder_{}-{}'.format(app_name, name)

    def get_emails(self, object):
        adddresses = []
        default_addr = getattr(settings, 'DEFAULT_USER_EMAIL', None)

        if default_addr:
            adddresses.append(default_addr)
        else:
            logger.critical('Reminder: the setting DEFAULT_USER_EMAIL has not been filled ; no email will be sent.')

        return adddresses

    def generate_email_subject(self, object):
        pass

    def generate_email_body(self, object):
        pass

    def get_Q_filter(self):  # TODO: get_queryset instead ????
        pass

    def ok_for_continue(self):
        return True

    def send_mails(self, instance, job):
        body    = self.generate_email_body(instance)
        subject = self.generate_email_subject(instance)

        EMAIL_SENDER = settings.EMAIL_SENDER
        messages = [EmailMessage(subject, body, EMAIL_SENDER, [email])
                        for email in self.get_emails(instance)
                   ]

        try:
            with get_connection() as connection:
                connection.send_messages(messages)
        except Exception as e:
            logger.critical('Error while sending reminder emails (%s)', e)
            JobResult.objects.create(
                job=job,
                messages=[
                    _('An error occurred while sending emails related to «{model}»').format(
                        model=self.model._meta.verbose_name,
                    ),
                    _('Original error: {}').format(e),
                ],
            )

            return False

        return True  # Means 'OK'

    def execute(self, job):
        if not self.ok_for_continue():
            return

        dt_now = now().replace(microsecond=0, second=0)

        for instance in self.model.objects.filter(self.get_Q_filter()).exclude(reminded=True):
            self.send_mails(instance, job)

            with atomic():
                DateReminder.objects.create(date_of_remind=dt_now,
                                            ident=FIRST_REMINDER,
                                            object_of_reminder=instance,
                                           )

                instance.reminded = True
                instance.save()

    def next_wakeup(self, now_value):
        """Returns the next time when the job manager should wake up in order
        to send the related e-mails.
        @param now_value: datetime object representing 'now'.
        @return None -> the job has not to be woke up.
                A datetime instance -> the job should be woke up at this time.
                    If it's in the past, it means the job should be run immediately
                    (tip: you can simply return now_value).
        """
        raise NotImplementedError


class ReminderRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._reminders = {}

    def register(self, reminder):  # TODO: rename 'reminder_class'
        """Register a class of Reminder.
        @type reminder: Class "inheriting" creme_core.core.reminder.Reminder.
        """
        reminders = self._reminders
        reminder_id = reminder.id

        if reminder_id in reminders:
            raise self.RegistrationError("Duplicated reminder's id or reminder registered twice: {}".format(reminder_id))

        reminders[reminder_id] = reminder()

    def unregister(self, reminder):
        if self._reminders.pop(reminder.id, None) is None:
            raise self.RegistrationError('No reminder is registered with this ID : {}'.format(reminder.id))

    def __iter__(self):
        return iter(self._reminders.values())

    # def itervalues(self):
    #     warnings.warn('ReminderRegistry.itervalues() is deprecated; use __iter__() instead.',
    #                   DeprecationWarning
    #                  )
    #
    #     return iter(self._reminders.values())


reminder_registry = ReminderRegistry()
