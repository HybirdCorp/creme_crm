# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django_extensions.management.jobs import HourlyJob

from creme_core.models import Lock

from recurrents.models import RecurrentGenerator

#from logging import debug
from datetime import datetime, timedelta

LOCK_NAME = "generate_recurrent_documents"

#NB: python manage.py runjob generate_document

class Job(HourlyJob):
    help = "Generate all recurrent documents that have to be."

    def execute(self):
        lock = Lock.objects.filter(name=LOCK_NAME)

        if not lock:
            lock = Lock(name=LOCK_NAME)
            lock.save()

            try:
                #debug("Y'a t-il des trucs à générer ???")
                for generator in RecurrentGenerator.objects.filter(is_working=True):
                    recurrent_date = generator.last_generation + timedelta(days = generator.periodicity.value_in_days)

                    last  = generator.last_generation
                    first = generator.first_generation
                    now   = datetime.now()

                    if recurrent_date < now or (last == first and first < now):
                        #debug("=== > Oui ! Génération en cours...")

                        template = generator.template.get_real_entity()

                        template.create_entity()
                        #debug("Pour le générateur <%s>, génération de <%s> effectué" % (generator,document))

                        generator.last_generation = datetime.now()
                        generator.save()
            finally:
                lock.delete()
        else:
            print 'A process is already running'
