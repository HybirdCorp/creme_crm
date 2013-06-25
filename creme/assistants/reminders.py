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

from datetime import timedelta #datetime

from django.db.models import Q
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.conf import settings

from creme.creme_core.core.reminder import Reminder

from .models import Alert, ToDo


class ReminderAlert(Reminder):
    id_    = Reminder.generate_id('assistants', 'alert')
    model_ = Alert

    def generate_email_subject(self, object):
        return _(u'Reminder concerning a Creme CRM alert related to %s') % object.creme_entity

    def generate_email_body(self, object):
        return _(u"""This mail is automatically sent by Crème CRM to remind you that an alert concerning %(entity)s will expire.
            Alert : %(title)s.
            which description is : %(description)s.

            which is related to the entity : %(entity)s""") % {
                    'entity':      object.creme_entity,
                    'title':       object.title,
                    'description': object.description,
                }

    def get_Q_filter(self):
        delta = timedelta(minutes=getattr(settings, 'DEFAULT_TIME_ALERT_REMIND', 30))
        dt_now = now().replace(microsecond=0, second=0)
        return Q(trigger_date__lte=dt_now - delta, is_validated=False)


class ReminderTodo(Reminder):
    id_    = Reminder.generate_id('assistants', 'todo')
    model_ = ToDo

    def generate_email_subject(self, object):
        return _(u'Reminder concerning a Creme CRM todo related to %s') % object.creme_entity

    def generate_email_body(self, object):
        return _(u"""This mail is automatically sent by Crème CRM to remind you that a todo concerning %(entity)s will expire.
            Todo : %(title)s.
            which description is : %(description)s.

             which is related to the entity : %(entity)s""") % {
                    'entity':      object.creme_entity,
                    'title':       object.title,
                    'description': object.description,
                }

    def get_Q_filter(self):
        delta = timedelta(days=1)
        dt_now = now().replace(microsecond=0, second=0)
        return Q(deadline__lte=dt_now + delta, is_ok=False)

    def ok_for_continue(self):
        return now().hour > 8


reminder_alert = ReminderAlert()
reminder_todo  = ReminderTodo()
