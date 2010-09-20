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

import re

from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _

from crudity import CREATE
from crudity.models.actions import WaitingAction
from crudity.models.history import History

passwd_pattern = re.compile(r'password=(?P<password>\w+)')

class CreateFromEmailBackend(object):
    password       = u""  #Password in body to verify permission
    limit_froms    = ()   #Email addresses
    in_sandbox     = True #Show in sandox (if False can be shown only in history & the creation will be automatic)
    body_map       = {}   #Mapping email body's key <==> model's key, value in the dict is the default value
    model          = None #Target model
    type           = CREATE
    subject        = u""#Matched subject

    def __init__(self):
        self.body_map.update({'password': self.password})

    def create(self, email):
        limit_froms = self.limit_froms
        data = self.body_map.copy()

        if not limit_froms or set(email.senders) & set(limit_froms):
            password = self.password
            body = email.body_html or email.body
            body = [line.replace(' ', '') for line in body.split('\n')]

            allowed = False

            #Search first the password
            for i, line in enumerate(body):
#                r = re.search(r'^password=(?P<password>\w+)', line)
                r = re.search(passwd_pattern, line)

                print "line :", line
                
                if r and r.groupdict().get('password') == password:
                    allowed = True
#                    body.pop(i)
                    break

            print "allowed :", allowed

            if allowed:
                for key in data.keys():
                    for i, line in enumerate(body):
                        r = re.search(r'%s=(?P<%s>\w+)' % (key, key), line)
                        if r:
                            data[key] = r.groupdict().get(key)
#                            body.pop(i)
                            break

                if self.in_sandbox:
                    action         = WaitingAction()
                    action.data    = action.set_data(data)
                    action.type    = CREATE
                    action.ct      = ContentType.objects.get_for_model(self.model)
                    action.be_name = self.subject
                    action.save()
                else:
                    self._create_instance_n_history(data)
                

    def create_from_waiting_action_n_history(self, action):
        return self._create_instance_n_history(action.get_data())

    def _create_instance_n_history(self, data):
        instance = self.model()
        instance.__dict__.update(data)
        is_created = True
        try:
            instance.save()
            history = History()
            history.entity = instance
#            history.entity_id = instance.pk
            history.type = self.type
#            history.ct = ContentType.objects.get_for_model(self.model)
            history.description = _(u"Creation of %(entity)s") % {'entity': instance}
            history.save()
        except IntegrityError:
            is_created = False

        return is_created


class DropFromEmailBackend(object):
    type = None

    def create(self, email):
        pass


drop_from_email_backend = DropFromEmailBackend()