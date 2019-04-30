# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2019  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.creme_jobs.base import JobType

from .models import UserMessage


class _UserMessagesSendType(JobType):
    id           = JobType.generate_id('assistants', 'usermessages_send')
    verbose_name = _('Send usermessages emails')
    periodic     = JobType.PSEUDO_PERIODIC

    def _execute(self, job):
        UserMessage.send_mails(job)

    # We have to implement it because it is a PSEUDO_PERIODIC JobType
    def next_wakeup(self, job, now_value):
        if UserMessage.objects.filter(email_sent=False).exists():
            return now_value


usermessages_send_type = _UserMessagesSendType()
jobs = (usermessages_send_type,)
