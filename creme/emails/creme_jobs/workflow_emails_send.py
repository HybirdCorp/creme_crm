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

from datetime import timedelta

from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_core.creme_jobs.base import JobType
from creme.emails.models import WorkflowEmail


class _WorkflowEmailsSendType(JobType):
    id = JobType.generate_id('emails', 'workflow_emails_send')
    verbose_name = _('Send Workflow emails')
    periodic = JobType.PSEUDO_PERIODIC

    # TODO: in settings? Setting value? Job data?
    RETRY_DELAY_MINUTES = 15
    REMOVE_SENT_DAYS = 15

    def _execute(self, job):
        Status = WorkflowEmail.Status

        for email in WorkflowEmail.objects.filter(
            status__in=[Status.NOT_SENT, Status.SENDING_ERROR],
        ):
            email.send()

        WorkflowEmail.objects.filter(
            status=Status.SENT,
            sending_date__lte=now() - timedelta(days=self.REMOVE_SENT_DAYS),
        ).delete()

    # We have to implement it because it is a PSEUDO_PERIODIC JobType
    def next_wakeup(self, job, now_value):
        Status = WorkflowEmail.Status
        filter_mail = WorkflowEmail.objects.filter

        if filter_mail(status=Status.NOT_SENT).exists():
            return now_value

        if filter_mail(status=Status.SENDING_ERROR).exists():
            # NB: if we regularly create EntityEmail with status SENDING_ERROR
            #     the wake-up is regularly delayed in the future (& so the job
            #     never re-run). It's probably not an issue because if the new
            #     e-mails have often an error status, your mail server is
            #     probably broken & you have more important issues...
            return now_value + timedelta(minutes=self.RETRY_DELAY_MINUTES)

        return None


workflow_emails_send_type = _WorkflowEmailsSendType()
