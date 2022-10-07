################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022  Hybird
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
from importlib import import_module

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from ..models import JobResult
from .base import JobType

logger = logging.getLogger(__name__)


class _SessionsCleanerType(JobType):
    id           = JobType.generate_id('creme_core', 'sessions_cleaner')
    verbose_name = gettext_lazy('Sessions cleaner')
    periodic     = JobType.PERIODIC

    def _execute(self, job):
        engine_path = settings.SESSION_ENGINE
        engine = import_module(engine_path)
        try:
            engine.SessionStore.clear_expired()
        except NotImplementedError:
            logger.warning(
                "Session engine '%s' doesn't support clearing expired "
                "sessions.",
                engine_path,
            )
            JobResult.objects.create(
                job=job,
                messages=[
                    _(
                        'The session engine does not support clearing. '
                        'Please contact your administrator.'
                    ),
                ],
            )

    def get_description(self, job):
        return [_("Remove expired user sessions")]


sessions_cleaner_type = _SessionsCleanerType()
