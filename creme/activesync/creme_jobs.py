# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.models import JobResult

from .errors import CremeActiveSyncError
from .sync import Synchronization


class _ActiveSyncType(JobType):
    id           = JobType.generate_id('activesync', 'synchronise')
    verbose_name = _('ActiveSync synchronisation')
    periodic     = JobType.PERIODIC

    def _execute(self, job):
        for user in get_user_model().objects.all():
            try:
                Synchronization(user).synchronize()
            except CremeActiveSyncError as e:
                JobResult.objects.create(job=job,
                                         errors=[ugettext(u'An error occurred for the user «%s»') % user,
                                                 ugettext(u'Original error: %s') % e,
                                                ],
                                        )

    def get_description(self, job):
        return [ugettext('Synchronise data with the ActiveSync server')]

    # def get_stats(self, job): TODO ??


activesync_type = _ActiveSyncType()
jobs = (activesync_type,)
