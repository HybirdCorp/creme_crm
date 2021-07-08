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

from django.db.models import Q
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_core.creme_jobs.base import JobType

from . import get_rgenerator_model


class _GenerateDocsType(JobType):
    id = JobType.generate_id('recurrents', 'generate_docs')
    verbose_name = _('Generate recurrent documents')
    periodic = JobType.PSEUDO_PERIODIC

    # TODO: we could add a field RecurrentGenerator.next_generation
    #  => queries would be more efficient
    def _get_generators(self, now_value):
        return get_rgenerator_model().objects.filter(
            is_working=True,
        ).filter(
            Q(
                last_generation__isnull=True,
                first_generation__lte=now_value,
            ) | Q(last_generation__isnull=False)
        )

    def _execute(self, job):
        # TODO: test is_working VS delete it (see next_wakeup() && job refreshing too)
        for generator in self._get_generators(now()):
            last = generator.last_generation
            next_generation = (
                generator.first_generation
                if last is None else
                last + generator.periodicity.as_timedelta()
            )

            if next_generation <= now():
                with atomic():
                    template = generator.template.get_real_entity()

                    template.create_entity()

                    generator.last_generation = next_generation
                    generator.save()

    # TODO: with docs generate the last time ?? (but stats will be cleaned at
    #       next run, even if nothing is generated...)
    # def get_stats(self, job):
    #     count = JobResult.objects.filter(job=job, raw_errors__isnull=True).count()
    #
    #     return [ungettext('%s entity has been successfully modified.',
    #                       '%s entities have been successfully modified.',
    #                       count
    #                      ) % count,
    #            ]

    # We have to implement it because it is a PSEUDO_PERIODIC JobType
    def next_wakeup(self, job, now_value):
        wakeup = None

        for generator in self._get_generators(now_value):
            last = generator.last_generation

            if last is None:  # We are sure that first_generation < now_value
                wakeup = now_value
                break

            recurrent_date = last + generator.periodicity.as_timedelta()
            wakeup = recurrent_date if not wakeup else min(wakeup, recurrent_date)

        return wakeup


recurrents_gendocs_type = _GenerateDocsType()
jobs = (recurrents_gendocs_type,)
