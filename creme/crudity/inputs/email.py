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
import re
from xml.etree import ElementTree as ET

from django.contrib.auth import get_user_model
from django.db.models import FieldDoesNotExist, FileField, ForeignKey
from django.utils.translation import gettext_lazy as _

from creme.documents import get_document_model

from ..backends.models import CrudityBackend
from ..constants import LEFT_MULTILINE_SEP, RIGHT_MULTILINE_SEP
from ..models import WaitingAction
from ..utils import strip_html, decode_b64binary  # strip_html_
from .base import CrudityInput

Document = get_document_model()
logger = logging.getLogger(__name__)

passwd_pattern = re.compile(r'password=(?P<password>\w+)', flags=re.IGNORECASE)
re_html_br     = re.compile(r'<br[/\s]*>')

assert len(LEFT_MULTILINE_SEP) == len(RIGHT_MULTILINE_SEP)

MULTILINE_SEP_LEN = len(RIGHT_MULTILINE_SEP)


class EmailInput(CrudityInput):
    name = 'raw'
    verbose_name = _('Email - Raw')

    def strip_html(self, html):
        # 'Manually' replace &nbsp; because we don't want \xA0 unicode char
        # TODO: improve strip_html() to give custom replacement ?
        html = re.sub(re_html_br, '\n', html).replace('&nbsp;', ' ')
        html = strip_html(html)
        # html = strip_html_(html)

        return html


class CreateEmailInput(EmailInput):
    method = 'create'
    verbose_method = _('Create')
    brickheader_action_templates = ('crudity/bricks/header-actions/email-creation-template.html',)

    def create(self, email):
        backend = self.get_backend(CrudityBackend.normalize_subject(email.subject)) # or self.get_backend("*")

        if backend is not None and self.authorize_senders(backend, email.senders):
            data = backend.body_map.copy()
            body = (self.strip_html(email.body_html) or email.body).replace('\r', '')

            # Multi-line handling
            left_idx = body.find(LEFT_MULTILINE_SEP)
            while left_idx > -1:
                right_idx = body.find(RIGHT_MULTILINE_SEP)

                if right_idx < left_idx:  # A RIGHT_MULTILINE_SEP is specified before LEFT_MULTILINE_SEP
                    body = body[:right_idx] + body[right_idx + MULTILINE_SEP_LEN:]
                    left_idx = body.find(LEFT_MULTILINE_SEP)
                    continue

                # The body excepted current LEFT_MULTILINE_SEP
                malformed_idx = (body[:left_idx] + body[left_idx + MULTILINE_SEP_LEN:right_idx]).find(LEFT_MULTILINE_SEP)

                if malformed_idx > -1:
                    # This means that a next occurrence of multiline is opened before closing current one
                    body = body[:left_idx] + body[left_idx + MULTILINE_SEP_LEN:]
                    left_idx = body.find(LEFT_MULTILINE_SEP)
                    continue

                if right_idx > -1:
                    body = body[:left_idx] + \
                           body[left_idx:right_idx + MULTILINE_SEP_LEN].replace('\n', '\\n') \
                                                                       .replace(LEFT_MULTILINE_SEP, '') \
                                                                       .replace(RIGHT_MULTILINE_SEP, '') + \
                           body[right_idx + MULTILINE_SEP_LEN:]
                    left_idx = body.find(LEFT_MULTILINE_SEP)
                else:
                    left_idx = -1
            # End Multiline handling

            split_body = [line.replace('\t', '') for line in body.split('\n') if line.strip()]

            if self.is_allowed_password(backend.password, split_body):
                for key in data.keys():
                    for i, line in enumerate(split_body):
                        r = re.search(r"""[\t ]*%s[\t ]*=(?P<%s>['"/@ \t.;?!-\\\w&]+)""" % (key, key), line, flags=re.UNICODE)

                        if r:
                            # TODO: Check if the target field is a simple-line field ?
                            # data[key] = (r.groupdict().get(key).replace('\\n', '\n')).encode('utf8')
                            data[key] = r.groupdict().get(key).replace('\\n', '\n')
                            split_body.pop(i)
                            break

                return self._create(backend, data, email.senders[0])

        return None

    def _pre_create(self, backend, data):
        pass

    def _post_create(self, backend, data, instance):
        pass

    def _pre_process_data(self, backend, data):
        pass

    def _create(self, backend, data, sender):
        data.pop('password', None)
        owner = self.get_owner(backend.is_sandbox_by_user, sender)

        self._pre_process_data(backend, data)

        if backend.in_sandbox:
            WaitingAction.objects.create(
                action='create',
                source='email - {}'.format(self.name),
                ct=backend.model,
                subject=backend.subject,
                user=owner,
                data=data,
            )
        else:
            self._pre_create(backend, data)
            is_created, instance = backend._create_instance_n_history(data, user=owner,
                                                                      source='email - {}'.format(self.name),
                                                                     )
            self._post_create(backend, data, instance)

        return backend

    @staticmethod
    def get_owner(is_sandbox_by_user, sender=None):
        """Returns the owner to assign to waiting actions and history"""
        owner = None

        if is_sandbox_by_user:
            User = get_user_model()
            owner = User.objects.filter(email=sender).first() or User.objects.get_admin()

        return owner

    def is_allowed_password(self, password, split_body):
        allowed = False
        # Search first the password
        for i, line in enumerate(split_body):
            line = line.replace(' ', '')
            r = re.search(passwd_pattern, line)

            if r and r.groupdict().get('password') == password:
                allowed = True
                break

        return allowed


remove_pattern = re.compile('[\t\n\r\f\v]')


class CreateInfopathInput(CreateEmailInput):
    name         = 'infopath'
    verbose_name = _('Email - Infopath')
    brickheader_action_templates = ('crudity/bricks/header-actions/infopath-creation-form.html',)

    MIME_TYPES = ['application/x-microsoft-infopathform']

    def _pre_process_data(self, backend, data):
        model_get_field = backend.model._meta.get_field

        for field_name, field_value in data.items():
            try:
                field = model_get_field(field_name)
            except FieldDoesNotExist:
                continue

            if field_value is not None \
               and (isinstance(field, ForeignKey) and issubclass(field.remote_field.model, Document)) \
               or isinstance(field, FileField):
                data[field_name] = decode_b64binary(field_value.encode())  # (filename, image_blob)

    def create(self, email):
        backend = self.get_backend(CrudityBackend.normalize_subject(email.subject)) or self.get_backend("*")

        if backend is None:
            return None

        MIME_TYPES = self.MIME_TYPES
        attachments = [a for a in email.attachments if a[1].content_type in MIME_TYPES]

        if attachments and self.authorize_senders(backend, email.senders):
            body = (self.strip_html(email.body_html) or email.body).replace('\r', '')
            split_body = [line.replace('\t', '') for line in body.split('\n') if line.strip()]

            if self.is_allowed_password(backend.password, split_body):
                is_created = False
                for data in filter(lambda x: x is not None,
                                   (self.get_data_from_infopath_file(backend, attachment)
                                        for name, attachment in attachments
                                   )
                                  ):
                    self._create(backend, data, email.senders[0])
                    is_created = True

                if is_created:
                    return backend

    def get_data_from_infopath_file(self, backend, xml_file):
        content = xml_file.read().decode()
        content = re.sub(remove_pattern, '', content.strip(), re.U)
        content = re.sub(r'>[\s]*<', '><', content, re.U)

        if not content:
            return None

        try:
            xml = ET.fromstring(content)
        except Exception as e:  # ExpatError in py2.6, ParseError in py2.7...
            logger.error('CreateInfopathInput.get_data_from_infopath_file(): %s', e)
            return None

        data = backend.body_map.copy()
        for node in xml:
            try:
                tag = re.search(r'[{].*[}](?P<tag>[-_\d\s\w]+)', node.tag).groupdict()['tag']  # TODO: compile
            except AttributeError:
                continue

            # if data.has_key(tag):
            if tag in data:
                children = list(node)

                if children:  # Multi-line
                    data[tag] = '\n'.join(child.text or '' for child in children)
                else:
                    data[tag] = node.text

        return data
