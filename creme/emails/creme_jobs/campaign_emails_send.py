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

from django.db.models.query_utils import Q
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _  # ugettext

from creme.creme_core.creme_jobs.base import JobType

from ..models import EmailSending
from ..models.sending import (SENDING_TYPE_IMMEDIATE, SENDING_TYPE_DEFERRED,
        SENDING_STATE_DONE, SENDING_STATE_INPROGRESS)


class _CampaignEmailsSendType(JobType):
    id           = JobType.generate_id('emails', 'campaign_emails_send')
    verbose_name = _('Send emails from campaigns')
    periodic     = JobType.PSEUDO_PERIODIC

    def _execute(self, job):
        for sending in EmailSending.objects.exclude(campaign__is_deleted=True) \
                                           .exclude(state=SENDING_STATE_DONE) \
                                           .filter(Q(type=SENDING_TYPE_IMMEDIATE) |
                                                   Q(sending_date__lte=now())
                                                  ):
            sending.state = SENDING_STATE_INPROGRESS
            sending.save()

            # if getattr(settings, 'REMOTE_STATS', False):
            #     from creme.emails.utils.remoteutils import populate_minicreme #broken
            #     populate_minicreme(sending)

            status = sending.send_mails()

            # TODO: move in send_mails() ???
            sending.state = status or SENDING_STATE_DONE
            sending.save()

    # def get_description(self, job):
    #     return [ugettext('Send all un-sent mails that have to be.')]

    def next_wakeup(self, job, now_value):  # We have to implement it because it is a PSEUDO_PERIODIC JobType
        qs = EmailSending.objects.exclude(campaign__is_deleted=True) \
                                 .exclude(state=SENDING_STATE_DONE)

        if qs.filter(type=SENDING_TYPE_IMMEDIATE).exists():
            return now_value

        dsending = qs.filter(type=SENDING_TYPE_DEFERRED).order_by('sending_date').first()

        return dsending.sending_date if dsending is not None else None


campaign_emails_send_type = _CampaignEmailsSendType()
