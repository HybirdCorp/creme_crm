################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.timezone import now
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..core.notification import OUTPUT_EMAIL
from ..models import JobResult, Notification
from ..utils.dates import dt_to_ISO8601
from .base import JobType

logger = logging.getLogger(__name__)


class _NotificationEmailsSenderType(JobType):
    id           = JobType.generate_id('creme_core', 'notification_emails_sender')
    verbose_name = _('Send notification emails')
    periodic     = JobType.PSEUDO_PERIODIC

    # TODO: in job configurable data?
    subject_prefix = _('[Notification from {software}] {subject}')

    def _get_notifications(self):
        return Notification.objects.filter(
            output=OUTPUT_EMAIL, extra_data__sent__isnull=True,
        )

    # TODO: use chunks?
    def _execute(self, job):
        # TODO: <sleep(10)> to be sure the transaction which trigger the refreshing is finished?
        notifications = self._get_notifications()
        EMAIL_SENDER = settings.EMAIL_SENDER
        messages = []

        for notif in notifications:
            user = notif.user
            content = notif.content

            msg = EmailMultiAlternatives(
                subject=self.subject_prefix.format(
                    software=settings.SOFTWARE_LABEL,
                    subject=content.get_subject(user=user),
                ),
                body=content.get_body(user=user),
                from_email=EMAIL_SENDER,
                to=[user.email],
            )
            html_body = content.get_html_body(user=user)
            if html_body:
                msg.attach_alternative(html_body, 'text/html')

            messages.append(msg)

        try:
            with get_connection() as connection:
                connection.send_messages(messages)
        except Exception as e:
            logger.critical('Error while sending reminder emails (%s)', e)
            JobResult.objects.create(
                job=job,
                messages=[
                    gettext("An error occurred while sending notification's emails"),
                    gettext('Original error: {}').format(e),
                ],
            )

        # TODO: mark error to be able to send again?
        notifications.update(extra_data={'sent': dt_to_ISO8601(now())})

    # We have to implement it because it is a PSEUDO_PERIODIC JobType
    def next_wakeup(self, job, now_value):
        if self._get_notifications().exists():
            return now_value

        return None


notification_emails_sender_type = _NotificationEmailsSenderType()
