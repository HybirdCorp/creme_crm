################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from collections.abc import Iterable

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from creme.creme_core.utils.html import strip_html
from creme.documents import get_document_model

from ..backends.models import CrudityBackend
from ..constants import LEFT_MULTILINE_SEP, RIGHT_MULTILINE_SEP
from ..fetchers.pop import PopEmail
from ..models import WaitingAction
from ..utils import is_sandbox_by_user
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

    def strip_html(self, html: str) -> str:
        # 'Manually' replace &nbsp; because we don't want \xA0 unicode char
        # TODO: improve strip_html() to give custom replacement ?
        html = re.sub(re_html_br, '\n', html).replace('&nbsp;', ' ')
        html = strip_html(html)

        return html


class CreateEmailInput(EmailInput):
    method = 'create'
    verbose_method = _('Create')
    brickheader_action_templates = ('crudity/bricks/header-actions/email-creation-template.html',)

    def create(self, email: PopEmail):
        backend = self.get_backend(CrudityBackend.normalize_subject(email.subject))

        if backend is not None and self.authorize_senders(backend, email.senders):
            data = backend.body_map.copy()
            body = (self.strip_html(email.body_html) or email.body).replace('\r', '')

            # Multi-line handling
            left_idx = body.find(LEFT_MULTILINE_SEP)
            while left_idx > -1:
                right_idx = body.find(RIGHT_MULTILINE_SEP)

                if right_idx < left_idx:
                    # A RIGHT_MULTILINE_SEP is specified before LEFT_MULTILINE_SEP
                    body = body[:right_idx] + body[right_idx + MULTILINE_SEP_LEN:]
                    left_idx = body.find(LEFT_MULTILINE_SEP)
                    continue

                # The body excepted current LEFT_MULTILINE_SEP
                malformed_idx = (
                    body[:left_idx] + body[left_idx + MULTILINE_SEP_LEN:right_idx]
                ).find(LEFT_MULTILINE_SEP)

                if malformed_idx > -1:
                    # This means that a next occurrence of multiline is opened
                    # before closing current one
                    body = body[:left_idx] + body[left_idx + MULTILINE_SEP_LEN:]
                    left_idx = body.find(LEFT_MULTILINE_SEP)
                    continue

                if right_idx > -1:
                    body = (
                        body[:left_idx]
                        + body[
                            left_idx:right_idx + MULTILINE_SEP_LEN
                        ].replace('\n', '\\n')
                         .replace(LEFT_MULTILINE_SEP, '')
                         .replace(RIGHT_MULTILINE_SEP, '')
                        + body[right_idx + MULTILINE_SEP_LEN:]
                    )
                    left_idx = body.find(LEFT_MULTILINE_SEP)
                else:
                    left_idx = -1
            # End Multiline handling

            split_body = [line.replace('\t', '') for line in body.split('\n') if line.strip()]

            if self.is_allowed_password(backend.password, split_body):
                for key in data.keys():
                    for i, line in enumerate(split_body):
                        r = re.search(
                            fr"""[\t ]*{key}[\t ]*=(?P<{key}>['"/@ \t.;?!-\\\w&]+)""",
                            line,
                            flags=re.UNICODE,
                        )

                        if r:
                            # TODO: Check if the target field is a simple-line field ?
                            data[key] = r[key].replace('\\n', '\n')
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
        owner = self.get_owner(is_sandbox_by_user(), sender)

        self._pre_process_data(backend, data)

        if backend.in_sandbox:
            WaitingAction.objects.create(
                action='create',
                source=f'email - {self.name}',
                ct=backend.model,
                subject=backend.subject,
                user=owner,
                data=data,
            )
        else:
            self._pre_create(backend, data)
            is_created, instance = backend._create_instance_n_history(
                data,
                user=owner,
                source=f'email - {self.name}',
            )
            self._post_create(backend, data, instance)

        return backend

    @staticmethod
    def get_owner(is_sandbox_by_user: bool, sender: str | None = None):
        """Returns the owner to assign to waiting actions and history"""
        owner = None

        if is_sandbox_by_user:
            User = get_user_model()
            # TODO: search even if email is None ?
            owner = User.objects.filter(email=sender).first() or User.objects.get_admin()

        return owner

    def is_allowed_password(self, password: str, split_body: Iterable[str]) -> bool:
        allowed = False
        # Search first the password
        for i, line in enumerate(split_body):
            line = line.replace(' ', '')
            r = re.search(passwd_pattern, line)

            if r and r.groupdict().get('password') == password:
                allowed = True
                break

        return allowed
