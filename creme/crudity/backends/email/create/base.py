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
import datetime, time

import re

from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import ugettext as _
from django.utils import formats

from creme_core.utils.meta import is_date_field

from crudity import CREATE
from crudity.models.actions import WaitingAction
from crudity.models.history import History
from crudity.blocks import WaitingActionBlock
from crudity.utils import strip_html, strip_html_

passwd_pattern = re.compile(r'password=(?P<password>\w+)')
re_html_br     = re.compile(r'<br[/\s]*>')

class CreateFromEmailBackend(object):
    password       = u""  #Password in body to verify permission
    limit_froms    = ()   #Email addresses
    in_sandbox     = True #Show in sandox (if False can be shown only in history & the creation will be automatic)
    body_map       = {}   #Mapping email body's key <==> model's key, value in the dict is the default value
    model          = None #Target model
    type           = CREATE
    subject        = u""  #Matched subject
    blocks         = (WaitingActionBlock, )#Rendered blocks

    def __init__(self):
        self.body_map.update({'password': self.password})

    def authorize_senders(self, senders):
        return not self.limit_froms or set(senders) & set(self.limit_froms)
    
    def create(self, email, request=None):
        data = self.body_map.copy()

        if self.authorize_senders(email.senders):
            password = self.password
            body = email.body_html or email.body

            if email.body_html:
                #TODO: Not really good to have parse twice to strip...
                body = re.sub(re_html_br, '\n', body)
                body = strip_html(body)
                body = strip_html_(body)

            body = body.replace('\r', '')
            splited_body = [line for line in body.split('\n') if line.strip()]
            bodyc= splited_body
            bodyp = [line.replace(' ', '') for line in splited_body]

            allowed = False

            #Search first the password
            for i, line in enumerate(bodyp):
                r = re.search(passwd_pattern, line)

                if r and r.groupdict().get('password') == password:
                    allowed = True
#                    bodyp.pop(i)
                    break

            if allowed:
                for key in data.keys():
                    for i, line in enumerate(bodyc):
#                        r = re.search(r"""[\t ]*%s[\t ]*=(?P<%s>['"/@ \t.;?!\\\w]+)""" % (key, key), line)
                        r = re.search(ur"""[\t ]*%s[\t ]*=(?P<%s>['"/@ \t.;?!\\\w&]+)""" % (key, key), line, flags=re.UNICODE)

                        if r:
                            data[key] = r.groupdict().get(key)
                            bodyc.pop(i)
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

        model_get_field = self.model._meta.get_field

        for field_name, field_value in data.iteritems():
            try:
                if is_date_field(model_get_field(field_name)):
                    for format in formats.get_format('DATETIME_INPUT_FORMATS'):#TODO: Extract this into a method?
                        try:
                            data[field_name] = datetime.datetime(*time.strptime(field_value, format)[:6])
                            break
                        except ValueError:
                            continue
            except FieldDoesNotExist:
                continue

        instance.__dict__.update(data)
        is_created = True
        try:
            instance.save()
            history = History()
            history.entity = instance
            history.type = self.type
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