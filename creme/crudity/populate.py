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

from functools import partial

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from creme.creme_core.gui.menu import ContainerEntry, Separator1Entry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import Job, MenuConfigItem, SettingValue
from creme.creme_core.utils.date_period import date_period_registry

from . import menu
from .creme_jobs import crudity_synchronize_type
from .setting_keys import sandbox_key


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self):
        SettingValue.objects.get_or_create(key_id=sandbox_key.id, defaults={'value': False})

        user = get_user_model().objects.get_admin()
        Job.objects.get_or_create(
            type_id=crudity_synchronize_type.id,
            defaults={
                'language':    settings.LANGUAGE_CODE,
                'periodicity': date_period_registry.get_period('minutes', 30),
                'status':      Job.STATUS_OK,
                'data':        {'user': user.id},
            },
        )

        # ---------------------------
        # TODO: move to a "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='crudity-').exists():
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Tools')},
                defaults={'order': 100},
            )[0]

            create_mitem = partial(MenuConfigItem.objects.create, parent=container)
            create_mitem(
                entry_id=Separator1Entry.id,
                entry_data={'label': _('External data')},
                order=250,
            )
            create_mitem(entry_id=menu.WaitingActionsEntry.id, order=255)
            create_mitem(entry_id=menu.CrudityHistoryEntry.id, order=260)
