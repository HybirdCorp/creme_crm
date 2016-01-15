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

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.utils.timezone import now


LOCK_NAME = "generate_recurrent_documents"

# NB: python manage.py recurrents_gendocs


class Command(BaseCommand):
    help = "Generate all recurrent documents that have to be."

    def handle(self, *args, **options):
        from creme.creme_core.models.lock import Mutex, MutexLockedException
        # from creme.recurrents.models import RecurrentGenerator
        from creme.recurrents import get_rgenerator_model

        try:
            lock = Mutex.get_n_lock(LOCK_NAME)
        except MutexLockedException:
            self.stderr.write('A process is already running')
        else:
            for generator in get_rgenerator_model().objects.filter(is_working=True):
                last = generator.last_generation
                next_generation = generator.first_generation if last is None else \
                                  last + generator.periodicity.as_timedelta()

                if next_generation <= now():
                    with atomic():
                        template = generator.template.get_real_entity()

                        template.create_entity()

                        generator.last_generation = next_generation
                        generator.save()

            Mutex.graceful_release(LOCK_NAME)
