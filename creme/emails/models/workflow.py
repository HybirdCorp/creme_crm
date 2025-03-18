################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from __future__ import annotations

from .. import utils
from . import _Email


class WorkflowEmailSender(utils.EMailSender):
    def __init__(self, wf_email: WorkflowEmail):
        super().__init__(
            sender_address=wf_email.sender,
            body=wf_email.body,
            body_html=wf_email.body,
            # body_html=wf_email.body_html,  # TODO
        )

    def get_subject(self, mail):
        return mail.subject


class WorkflowEmail(_Email):
    email_sender_cls = WorkflowEmailSender

    class Meta:
        app_label = 'emails'

    # def __str__(self):
    #     return (
    #         f'WorkflowEmail<from: {self.sender}> '
    #         f'<to: {self.recipient}> '
    #         f'<sent: {self.sending_date}> '
    #         f'<id: {self.id}>'
    #     )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # TODO: in a signal handler?
        from ..creme_jobs import workflow_emails_send_type
        workflow_emails_send_type.refresh_job()

    def send(self):
        sender = self.email_sender_cls(self)
        sender.send(self)
        # if sender.send(self):
        #     logger.debug('Mail sent to %s', self.recipient)
