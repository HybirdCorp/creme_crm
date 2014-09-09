# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from functools import partial
import logging

from django.core.mail import EmailMessage, get_connection
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.transaction import commit_on_success
from django.utils.timezone import now

from ..models import DateReminder


logger = logging.getLogger(__name__)
FIRST_REMINDER = 1


class Reminder(object):
    id    = None   #overload with an unicode object ; use generate_id()
    model = None   #overload with a CremeModel

    def __init__(self):
        pass

    @staticmethod
    def generate_id(app_name, name):
        return u'reminder_%s-%s' % (app_name, name)

    def get_emails(self, object):
        return [getattr(settings, 'DEFAULT_USER_EMAIL', None)]

    def generate_email_subject (self, object):
        pass

    def generate_email_body(self, object):
        pass

    def get_Q_filter(self): #TODO: get_queryset instead ????
        pass

    def ok_for_continue (self):
        return True

    def send_mails(self, instance):
        body    = self.generate_email_body(instance)
        subject = self.generate_email_subject(instance)

        EMAIL_SENDER = settings.EMAIL_SENDER
        messages = [EmailMessage(subject, body, EMAIL_SENDER, [email])
                        for email in self.get_emails(instance)
                   ]

        try:
            connection = get_connection()
            connection.open()
            connection.send_messages(messages)
            connection.close()
        except Exception:
            logger.exception('Reminder.send_mails() failed')

            return False

        return True #means 'OK'

    def execute(self):
        if not self.ok_for_continue():
            return

        model = self.model
        dt_now = now().replace(microsecond=0, second=0)
        reminder_filter = partial(DateReminder.objects.filter,
                                  model_content_type=ContentType.objects.get_for_model(model),
                                 )

        #for instance in model.objects.filter(self.get_Q_filter()):
            #if not reminder_filter(model_id=instance.id).exists():
                #self.send_mails(instance)
                #DateReminder.objects.create(date_of_remind=dt_now,
                                            #ident=FIRST_REMINDER,
                                            #object_of_reminder=instance,
                                           #)

        for instance in model.objects.filter(self.get_Q_filter()).exclude(reminded=True):
            #if self.send_mails(instance): #problem -> job is runned immediatly/indefinitely because reminded flag is not set
            self.send_mails(instance)

            with commit_on_success():
                DateReminder.objects.create(date_of_remind=dt_now,
                                            ident=FIRST_REMINDER,
                                            object_of_reminder=instance,
                                           )

                instance.reminded = True
                instance.save()


class ReminderRegistry(object):
    def __init__(self):
        self._reminders = {}

    def register(self, reminder):
        """
        @type reminder creme_core.core.reminder.Reminder
        """
        reminders = self._reminders
        reminder_id = reminder.id

        if reminders.has_key(reminder_id):
            logger.warning("Duplicate reminder's id or reminder registered twice : %s", reminder_id) #exception instead ???

        reminders[reminder_id] = reminder

    def __iter__(self):
        return self._reminders.iteritems()

    def itervalues(self):
        return self._reminders.itervalues()


reminder_registry = ReminderRegistry()
