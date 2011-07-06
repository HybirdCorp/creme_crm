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

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import ugettext as _

from creme_config.models.setting import SettingValue

from creme_core.utils.dates import get_dt_from_str
from creme_core.utils.meta import is_date_field

from persons.models.contact import Contact

from crudity import CREATE
from crudity.constants import LEFT_MULTILINE_SEP, RIGHT_MULTILINE_SEP, SETTING_CRUDITY_SANDBOX_BY_USER
from crudity.models.actions import WaitingAction
from crudity.models.history import History
from crudity.blocks import WaitingActionBlock
from crudity.utils import strip_html, strip_html_

passwd_pattern = re.compile(r'password=(?P<password>\w+)', flags=re.IGNORECASE)
re_html_br     = re.compile(r'<br[/\s]*>')

assert len(LEFT_MULTILINE_SEP) == len(RIGHT_MULTILINE_SEP)

MULTILINE_SEP_LEN = len(RIGHT_MULTILINE_SEP)

class CreateFromEmailBackend(object):
    password        = u""  #Password in body to verify permission
    limit_froms     = ()   #Email addresses
    in_sandbox      = True #Show in sandox (if False can be shown only in history & the creation will be automatic)
    body_map        = {}   #Mapping email body's key <==> model's key, value in the dict is the default value
    model           = None #Target model
    type            = CREATE
    subject         = u""  #Matched subject
    blocks          = (WaitingActionBlock, )#Rendered blocks

    def __init__(self):
        self.body_map.update({'password': self.password})
        self._sandbox_by_user = None

    def _get_is_sandbox_by_user(self):
        if self._sandbox_by_user is None:
            self._sandbox_by_user = SettingValue.objects.get(key=SETTING_CRUDITY_SANDBOX_BY_USER, user=None).value
        return self._sandbox_by_user

    def _set_is_sandbox_by_user(self, value):
        self._sandbox_by_user = value

    is_sandbox_by_user = property(_get_is_sandbox_by_user, _set_is_sandbox_by_user);del _get_is_sandbox_by_user, _set_is_sandbox_by_user

    def authorize_senders(self, senders):
        return not self.limit_froms or set(senders) & set(self.limit_froms)

    def get_owner(self, sender=None):
        """Returns the owner to assign to waiting actions and history"""
        if self.is_sandbox_by_user:
            try:
                return Contact.objects.filter(email__iexact=sender, is_user__isnull=False)[0].is_user
            except IndexError:
                return User.objects.filter(is_superuser=True).order_by('-pk')[0]#No need to catch IndexError
        return None

    def create(self, email, current_user=None):
        data = self.body_map.copy()

        if self.authorize_senders(email.senders):
            password = self.password
            body = email.body_html or email.body

            if email.body_html:
                #TODO: Not really good to have parse twice to strip...
                body = re.sub(re_html_br, '\n', body).replace('&nbsp;', ' ')#'Manually' replace &nbsp; because we don't want \xA0 unicode char
                body = strip_html(body)
                body = strip_html_(body)

            body = body.replace('\r', '')

            #Multiline handling
            left_idx = body.find(LEFT_MULTILINE_SEP)
            while left_idx > -1:
                right_idx = body.find(RIGHT_MULTILINE_SEP)

                if right_idx < left_idx:#A RIGHT_MULTILINE_SEP is specified before LEFT_MULTILINE_SEP
                    body = body[:right_idx]+body[right_idx+MULTILINE_SEP_LEN:]
                    left_idx = body.find(LEFT_MULTILINE_SEP)
                    continue

                malformed_idx = (body[:left_idx]+body[left_idx+MULTILINE_SEP_LEN:right_idx]).find(LEFT_MULTILINE_SEP)#The body excepted current LEFT_MULTILINE_SEP
                if malformed_idx > -1:#This means that a next occurrence of multiline is opened before closing current one
                    body = body[:left_idx]+body[left_idx+MULTILINE_SEP_LEN:]
                    left_idx = body.find(LEFT_MULTILINE_SEP)
                    continue

                if right_idx > -1:
                    body = body[:left_idx]+body[left_idx:right_idx+MULTILINE_SEP_LEN].replace('\n','\\n').replace(LEFT_MULTILINE_SEP, '').replace(RIGHT_MULTILINE_SEP, '')+body[right_idx+MULTILINE_SEP_LEN:]
                    left_idx = body.find(LEFT_MULTILINE_SEP)
                else:
                    left_idx = -1
            #End Multiline handling

            splited_body = [line.replace('\t', '') for line in body.split('\n') if line.strip()]
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
                        r = re.search(ur"""[\t ]*%s[\t ]*=(?P<%s>['"/@ \t.;?!-\\\w&]+)""" % (key, key), line, flags=re.UNICODE)

                        if r:
                            data[key] = r.groupdict().get(key).replace('\\n', '\n')#TODO: Check if the target field is a simple-line field ?
                            bodyc.pop(i)
                            break

                if self.in_sandbox:
                    action         = WaitingAction()
                    action.data    = action.set_data(data)
                    action.type    = CREATE
                    action.ct      = ContentType.objects.get_for_model(self.model)
                    action.be_name = self.subject
                    action.user    = self.get_owner(email.senders[0])
                    action.save()
                else:
                    self._create_instance_n_history(data, user=self.get_owner(email.senders[0]))

    def create_from_waiting_action_n_history(self, action):
        return self._create_instance_n_history(action.get_data(), action.user)

    def _create_instance_n_history(self, data, user=None):
        instance = self.model()

        model_get_field = self.model._meta.get_field

        for field_name, field_value in data.iteritems():
            try:
                if is_date_field(model_get_field(field_name)):
                    data[field_name] = get_dt_from_str(field_value.strip())
            except FieldDoesNotExist:
                continue

        instance.__dict__.update(data)
        is_created = True
        try:
            instance.save()
            history = History()
            history.entity = instance
            history.type = self.type
            history.user = user
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
