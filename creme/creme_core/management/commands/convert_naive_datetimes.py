# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013  Hybird
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

from __future__ import print_function

import pytz

from django.db.models import DateTimeField, get_models
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.timezone import make_naive, make_aware, utc


class Command(BaseCommand):
    help = """For DBRMS that do not store timezone, it converts all DateTimes in the database to UTC DateTimes.
Do not run it twice (or DateTimes will be shifted twice).
Use it to migrate an instance of Creme 1.2 to Creme 1.3.
"""
    args = ''

    def handle(self, *args, **options):
        db_engine = settings.DATABASES['default']['ENGINE']
        if db_engine not in ('django.db.backends.mysql', 'django.db.backends.sqlite3'):
            print('"%s" backend already manages timezones, no need to convert.' % db_engine)
            return

        tz = pytz.timezone(settings.TIME_ZONE)

        for model in get_models():
            fnames = [field.name 
                        for field in model._meta.local_fields
                            if isinstance(field, DateTimeField)
                     ]

            if fnames:
                mngr = model.objects

                for instance in mngr.all():
                    kwargs = dict()

                    for fname in fnames:
                        old_value = getattr(instance, fname)

                        if old_value:
                            try:
                                new_value = make_aware(make_naive(old_value, utc), tz)
                            except Exception as e:
                                print('Can not convert datetime %(field)s="%(value)s" for instance of model "%(app)s.%(model)s" (pk=%(pk)s) [%(error)s]' % {
                                            'field':    fname,
                                            'value':    old_value,
                                            'app':      model._meta.app_label,
                                            'model':    model.__name__,
                                            'pk':       instance.pk,
                                            'error':    e,
                                        }
                                    )
                            else:
                                kwargs[fname] = new_value

                    if kwargs:
                        mngr.filter(pk=instance.pk).update(**kwargs)
 
