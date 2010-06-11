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

from datetime import datetime, timedelta

from django.db.models import Q
from django.conf import settings

from creme_core.reminder import Reminder

from models import Alert, ToDo


class ReminderAlert(Reminder):
    id_    = Reminder.generate_id('assistants', 'alert')
    model_ = Alert

    def generate_email_subject(self, object):
        #TODO: i18n
        return u'rappel concernant une alerte Crème CRM à propos de %s' % (object.creme_entity,)

    def generate_email_body(self, object): #TODO: i18n
        entity = object.creme_entity
        return u"""Ce mail est envoyé automatiquement par Crème CRM pour vous rappeler qu'une alerte concernant %s va arriver à échéance. \r\n
            Alerte : %s \r\n 
            dont la description est : %s \r\n.

            qui est rattachée à la fiche : %s """ % (entity, object.title, object.description, entity) #TODO: use a dict instead

    def get_Q_filter(self):
        delta = timedelta(minutes=getattr(settings, 'DEFAULT_TIME_ALERT_REMIND', 30))
        now   = datetime.now().replace(microsecond=0, second=0)
        return Q(trigger_date__lte=now - delta, is_validated=False)


class ReminderTodo(Reminder):
    id_    = Reminder.generate_id('assistants', 'todo')
    model_ = ToDo

    def generate_email_subject(self, object):
        #TODO: i18n
        return u'rappel concernant une todo Crème CRM à propos de %s' % (object.creme_entity,)

    def generate_email_body(self, object): #TODO: i18n
        entity = object.creme_entity
        return u"""Ce mail est envoyé automatiquement par Crème CRM pour vous rappeler qu'une todo concernant %s va arriver à échéance. \r\n
            Todo : %s \r\n 
            dont la description est : %s \r\n.

            qui est rattachée à la fiche : %s """ % (entity, object.title, object.description, entity)

    def get_Q_filter(self):
        delta = timedelta(days=1)
        now   = datetime.now().replace(microsecond=0, second=0)
        return Q(deadline__lte=now + delta, is_ok=False)

    def ok_for_continue(self):
        return True if datetime.now().hour > 8 else False


reminder_alert = ReminderAlert()
reminder_todo  = ReminderTodo()
