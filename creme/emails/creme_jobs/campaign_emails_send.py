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

from django.db.models.query_utils import Q
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_core.creme_jobs.base import JobType

# from ..models.sending import (
#     SENDING_STATE_DONE,
#     SENDING_STATE_INPROGRESS,
#     SENDING_TYPE_DEFERRED,
#     SENDING_TYPE_IMMEDIATE,
# )
from ..models import EmailSending


class _CampaignEmailsSendType(JobType):
    id = JobType.generate_id('emails', 'campaign_emails_send')
    verbose_name = _('Send emails from campaigns')
    periodic = JobType.PSEUDO_PERIODIC

    def _execute(self, job):
        for sending in EmailSending.objects.exclude(
                campaign__is_deleted=True,
        ).exclude(
            # state=SENDING_STATE_DONE,
            state=EmailSending.State.DONE,
        ).filter(
            # Q(type=SENDING_TYPE_IMMEDIATE) | Q(sending_date__lte=now())
            Q(type=EmailSending.Type.IMMEDIATE) | Q(sending_date__lte=now())
        ):
            # sending.state = SENDING_STATE_INPROGRESS
            sending.state = EmailSending.State.IN_PROGRESS
            sending.save()

            # if getattr(settings, 'REMOTE_STATS', False):
            #     from creme.emails.utils.remoteutils import populate_minicreme #broken
            #     populate_minicreme(sending)

            status = sending.send_mails()

            # TODO: move in send_mails() ???
            # sending.state = status or SENDING_STATE_DONE
            sending.state = status or EmailSending.State.DONE
            sending.save()

    # We have to implement it because it is a PSEUDO_PERIODIC JobType
    def next_wakeup(self, job, now_value):
        qs = EmailSending.objects.exclude(
            campaign__is_deleted=True,
        ).exclude(state=EmailSending.State.DONE)  # state=SENDING_STATE_DONE

        # if qs.filter(type=SENDING_TYPE_IMMEDIATE).exists():
        if qs.filter(type=EmailSending.Type.IMMEDIATE).exists():
            return now_value

        # dsending = qs.filter(type=SENDING_TYPE_DEFERRED).order_by('sending_date').first()
        dsending = qs.filter(type=EmailSending.Type.DEFERRED).order_by('sending_date').first()

        return dsending.sending_date if dsending is not None else None


campaign_emails_send_type = _CampaignEmailsSendType()
