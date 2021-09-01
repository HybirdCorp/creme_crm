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

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from . import bricks, constants, creme_jobs, menu, sandboxes, setting_keys
from .gui.menu import ContainerEntry, Separator0Entry, Separator1Entry
from .management.commands.creme_populate import BasePopulator
from .models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    ButtonMenuItem,
    CaseSensitivity,
    Currency,
    Job,
    Language,
    MenuConfigItem,
    RelationType,
    Sandbox,
    SettingValue,
    Vat,
)
from .utils import create_if_needed
from .utils.date_period import date_period_registry


class Populator(BasePopulator):
    def populate(self):
        already_populated = RelationType.objects.filter(id=constants.REL_SUB_HAS).exists()

        if not CaseSensitivity.objects.exists():
            CaseSensitivity.objects.create(text='CasE')

        RelationType.objects.smart_update_or_create(
            (constants.REL_SUB_HAS, _('owns')),
            (constants.REL_OBJ_HAS, _('belongs to')),
        )

        # ---------------------------
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.block_opening_key.id,   defaults={'value': True})
        create_svalue(key_id=setting_keys.block_showempty_key.id, defaults={'value': True})
        create_svalue(key_id=setting_keys.currency_symbol_key.id, defaults={'value': True})

        # ---------------------------
        create_if_needed(
            Currency,
            {'pk': constants.DEFAULT_CURRENCY_PK},
            name=_('Euro'), local_symbol=_('€'), international_symbol=_('EUR'),
            is_custom=False,
        )

        # ---------------------------
        create_job = Job.objects.get_or_create
        create_job(
            type_id=creme_jobs.temp_files_cleaner_type.id,
            defaults={
                'language': settings.LANGUAGE_CODE,
                'periodicity': date_period_registry.get_period('days', 1),
                'status': Job.STATUS_OK,
                'data': {
                    'delay': date_period_registry.get_period('days', 1).as_dict()
                },
            },
        )
        create_job(
            type_id=creme_jobs.reminder_type.id,
            defaults={
                'language': settings.LANGUAGE_CODE,
                'status': Job.STATUS_OK,
            },
        )

        # ---------------------------

        Sandbox.objects.get_or_create(
            uuid=constants.UUID_SANDBOX_SUPERUSERS,
            defaults={
                # 'superuser': True,
                'type_id':   sandboxes.OnlySuperusersType.id,
            },
        )

        # ---------------------------
        if not MenuConfigItem.objects.filter(entry_id=menu.CremeEntry.id).exists():
            create_mitem = MenuConfigItem.objects.create
            create_mitem(entry_id=menu.CremeEntry.id, order=1)
            create_mitem(entry_id=Separator0Entry.id, order=2)

            tools = create_mitem(
                entry_id=ContainerEntry.id, entry_data={'label': _('Tools')},
                order=100,
            )
            create_mitem(entry_id=menu.JobsEntry.id, parent=tools, order=5)

            create_mitem(entry_id=Separator0Entry.id, order=1000)
            creations = create_mitem(
                entry_id=ContainerEntry.id, entry_data={'label': _('+ Creation')},
                order=1010,
            )
            create_mitem(
                entry_id=Separator1Entry.id, entry_data={'label': _('Main entities')},
                parent=creations, order=1,
            )
            create_mitem(
                entry_id=Separator1Entry.id, entry_data={'label': _('Quick creation')},
                parent=creations, order=100,
            )
            create_mitem(entry_id=menu.QuickFormsEntries.id,     parent=creations, order=101)
            create_mitem(entry_id=Separator1Entry.id,            parent=creations, order=200)
            create_mitem(entry_id=menu.EntitiesCreationEntry.id, parent=creations, order=201)

            create_mitem(entry_id=menu.RecentEntitiesEntry.id, order=1020)

        # ---------------------------
        if not already_populated:
            login = password = 'root'
            root = get_user_model().objects.create_superuser(
                pk=1, username=login, password=password,
                first_name='Fulbert', last_name='Creme',
                email=_('replaceMe@byYourAddress.com'),
            )

            if self.verbosity:
                self.stdout.write(
                    f'\n A super-user has been created with '
                    f'login="{login}" and password="{password}".',
                    self.style.NOTICE,
                )

            # ---------------------------
            create_if_needed(
                Currency, {'pk': 2},
                name=_('United States dollar'),
                local_symbol=_('$'), international_symbol=_('USD'),
            )

            # create_if_needed(Language, {'pk': 1}, name=_('French'),  code='FRA')
            # create_if_needed(Language, {'pk': 2}, name=_('English'), code='EN')
            Language.objects.bulk_create([
                Language(name=name)
                for name in [
                    _('English'),
                    _('French'),
                    _('German'),
                    _('Spanish'),
                    _('Chinese'),
                    _('Japanese'),
                    _('Italian'),
                    _('Portuguese'),
                    _('Dutch'),
                ]
            ])

            # ---------------------------
            BrickDetailviewLocation.objects.multi_create(
                defaults={'zone': BrickDetailviewLocation.LEFT},
                data=[
                    {'order': 5},
                    {'brick': bricks.CustomFieldsBrick, 'order': 40},
                    {'brick': bricks.PropertiesBrick,   'order': 450},
                    {'brick': bricks.RelationsBrick,    'order': 500},

                    {
                        'brick': bricks.HistoryBrick, 'order': 8,
                        'zone': BrickDetailviewLocation.RIGHT,
                    },

                ],
            )

            create_bhl = BrickHomeLocation.objects.create
            create_bhl(brick_id=bricks.StatisticsBrick.id_, order=8)
            create_bhl(brick_id=bricks.HistoryBrick.id_,    order=10)

            create_bml = BrickMypageLocation.objects.create
            create_bml(brick_id=bricks.HistoryBrick.id_, order=8, user=None)
            create_bml(brick_id=bricks.HistoryBrick.id_, order=8, user=root)

            # ---------------------------
            if not ButtonMenuItem.objects.filter(content_type=None).exists():
                ButtonMenuItem.objects.create(
                    content_type=None, button_id='', order=1,
                )

            # ---------------------------
            create_vat = Vat.objects.get_or_create
            DEFAULT_VAT = constants.DEFAULT_VAT
            for value in {
                *(
                    Decimal(value)
                    for value in ['0.0', '5.50', '7.0', '19.60', '20.0', '21.20']
                ),
                DEFAULT_VAT,
            }:
                create_vat(value=value, is_default=(value == DEFAULT_VAT), is_custom=False)

        if settings.TESTS_ON:
            from .tests import fake_populate
            fake_populate.populate()
