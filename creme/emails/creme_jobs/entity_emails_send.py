# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from datetime import timedelta

from django.utils.translation import gettext_lazy as _

from creme.creme_core.creme_jobs.base import JobType

# from ..constants import MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR
from .. import get_entityemail_model

ENTITY_EMAILS_RETRY = 15  # In minutes  TODO: in settings ? Setting value ? Job data ?
EntityEmail = get_entityemail_model()


class _EntityEmailsSendType(JobType):
    id = JobType.generate_id('emails', 'entity_emails_send')
    verbose_name = _('Send entity emails')
    periodic = JobType.PSEUDO_PERIODIC

    def _execute(self, job):
        Status = EntityEmail.Status

        for email in EntityEmail.objects.exclude(is_deleted=True).filter(
            # status__in=[MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR],
            status__in=[Status.NOT_SENT, Status.SENDING_ERROR],
        ):
            email.send()

    # We have to implement it because it is a PSEUDO_PERIODIC JobType
    def next_wakeup(self, job, now_value):
        Status = EntityEmail.Status
        filter_mail = EntityEmail.objects.exclude(is_deleted=True).filter

        # if filter_mail(status=MAIL_STATUS_NOTSENT).exists():
        if filter_mail(status=Status.NOT_SENT).exists():
            return now_value

        # if filter_mail(status=MAIL_STATUS_SENDINGERROR).exists():
        if filter_mail(status=Status.SENDING_ERROR).exists():
            return now_value + timedelta(minutes=ENTITY_EMAILS_RETRY)

        return None


entity_emails_send_type = _EntityEmailsSendType()
