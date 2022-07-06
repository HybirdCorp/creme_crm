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

import logging

from django.utils.translation import gettext_lazy as _

from ..creme_jobs import temp_files_cleaner_type
from .fields import DatePeriodField
from .job import JobForm

logger = logging.getLogger(__name__)


class TempFilesCleanerJobForm(JobForm):
    delay = DatePeriodField(label=_('Remove temporary files which are older than:'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        job = self.instance

        if job.pk:
            self.fields['delay'].initial = temp_files_cleaner_type.get_delay(job)

    def save(self, *args, **kwargs):
        self.instance.data = {'delay': self.cleaned_data['delay'].as_dict()}

        return super().save(*args, **kwargs)
