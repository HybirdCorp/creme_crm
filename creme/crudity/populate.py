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

from django.conf import settings
from django.contrib.auth import get_user_model

from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import SettingValue, Job
from creme.creme_core.utils.date_period import date_period_registry

from .creme_jobs import crudity_synchronize_type
from .setting_keys import sandbox_key


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        # SettingValue.create_if_needed(key=sandbox_key, user=None, value=False)
        SettingValue.objects.get_or_create(key_id=sandbox_key.id, defaults={'value': False})

        CremeUser = get_user_model()

        try:
            user = CremeUser.objects.get(pk=settings.CREME_GET_EMAIL_JOB_USER_ID)
        except (CremeUser.DoesNotExist, AttributeError):
            user = CremeUser.objects.get_admin()

        Job.objects.get_or_create(type_id=crudity_synchronize_type.id,
                                  defaults={'language':    settings.LANGUAGE_CODE,
                                            'periodicity': date_period_registry.get_period('minutes', 30),
                                            'status':      Job.STATUS_OK,
                                            'data':        {'user': user.id},
                                           }
                                 )
