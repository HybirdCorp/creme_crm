################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from . import (
    bricks,
    constants,
    creme_jobs,
    get_world_settings_model,
    menu,
    notification,
    sandboxes,
    setting_keys,
)
from .apps import CremeAppConfig, creme_app_configs
from .auth import EntityCredentials
from .core.notification import OUTPUT_EMAIL, OUTPUT_WEB
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
    NotificationChannel,
    RelationType,
    Sandbox,
    SetCredentials,
    SettingValue,
    UserRole,
    Vat,
)
from .registry import creme_registry
# from .utils import create_if_needed
from .utils.date_period import date_period_registry


class Populator(BasePopulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = None

    def _already_populated(self):
        return RelationType.objects.filter(id=constants.REL_SUB_HAS).exists()

    def _populate(self):
        get_world_settings_model().objects.get_or_create(pk=1)

        if not CaseSensitivity.objects.exists():
            CaseSensitivity.objects.create(text='CasE')

        super()._populate()
        self._populate_currencies()

        if settings.TESTS_ON:
            from .tests import fake_populate
            fake_populate.populate()

    def _first_populate(self):
        self._populate_root()
        super()._first_populate()
        self._populate_roles()
        self._populate_optional_currencies()
        self._populate_languages()
        self._populate_vats()

    def _populate_root(self):
        login = constants.ROOT_USERNAME
        password = constants.ROOT_PASSWORD
        self.root = get_user_model().objects.create_superuser(
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

    def _populate_roles(self):
        CRED_REGULAR = CremeAppConfig.CRED_REGULAR
        entity_models = [*creme_registry.iter_entity_models()]
        regular_role = UserRole.objects.smart_create(
            name=_('Regular user'),
            uuid='a97a66aa-a2c0-42bf-a6d0-a4d99b604cb3',
            allowed_apps=[
                app.label for app in creme_app_configs() if app.credentials & CRED_REGULAR
            ],
            creatable_models=entity_models,
            exportable_models=entity_models,
        )
        SetCredentials.objects.create(
            role=regular_role,
            # NB: EntityCredentials._ALL_CREDS set the bit 0 too...
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

    def _populate_currencies(self):
        # create_if_needed(
        #     Currency,
        #     {'pk': constants.DEFAULT_CURRENCY_PK},
        #     name=_('Euro'), local_symbol=_('€'), international_symbol=_('EUR'),
        #     is_custom=False,
        # )
        Currency.objects.get_or_create(
            id=constants.DEFAULT_CURRENCY_PK,
            defaults={
                'name': _('Euro'),
                'local_symbol': _('€'),
                'international_symbol': _('EUR'),
                'is_custom': False,
            },
        )

    def _populate_optional_currencies(self):
        # create_if_needed(
        #     Currency, {'pk': 2},
        #     name=_('United States dollar'),
        #     local_symbol=_('$'), international_symbol=_('USD'),
        # )
        Currency.objects.get_or_create(
            id=2,
            defaults={
                'name': _('United States dollar'),
                'local_symbol': _('$'),
                'international_symbol': _('USD'),
            },
        )

    def _populate_languages(self):
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

    def _populate_vats(self):
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

    def _populate_relation_types(self):
        RelationType.objects.smart_update_or_create(
            (constants.REL_SUB_HAS, _('owns')),
            (constants.REL_OBJ_HAS, _('belongs to')),
        )

    def _populate_jobs(self):
        create_job = Job.objects.get_or_create
        create_job(
            type_id=creme_jobs.sessions_cleaner_type.id,
            defaults={
                'language': settings.LANGUAGE_CODE,
                'periodicity': date_period_registry.get_period('days', 1),
                'status': Job.STATUS_OK,
            },
        )
        create_job(
            type_id=creme_jobs.temp_files_cleaner_type.id,
            defaults={
                'language': settings.LANGUAGE_CODE,
                'periodicity': date_period_registry.get_period('days', 1),
                'status': Job.STATUS_OK,
                'data': {
                    'delay': date_period_registry.get_period('days', 1).as_dict(),
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
        create_job(
            type_id=creme_jobs.notification_emails_sender_type.id,
            defaults={
                'language': settings.LANGUAGE_CODE,
                'status': Job.STATUS_OK,
            },
        )

    def _populate_sandboxes(self):
        Sandbox.objects.get_or_create(
            uuid=constants.UUID_SANDBOX_SUPERUSERS,
            defaults={
                # 'superuser': True,
                'type_id': sandboxes.OnlySuperusersType.id,
            },
        )

    def _populate_setting_values(self):
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.block_opening_key.id,   defaults={'value': True})
        create_svalue(key_id=setting_keys.block_showempty_key.id, defaults={'value': True})
        create_svalue(key_id=setting_keys.currency_symbol_key.id, defaults={'value': True})

    def _populate_notification_channels(self):
        create_channel = NotificationChannel.objects.get_or_create
        create_channel(
            uuid=constants.UUID_CHANNEL_SYSTEM,
            defaults={
                'type_id': notification.SystemChannelType.id,
                'required': True,
                'default_outputs': [OUTPUT_WEB],
            },
        )
        create_channel(
            uuid=constants.UUID_CHANNEL_ADMIN,
            defaults={
                'type_id': notification.AdministrationChannelType.id,
                'default_outputs': [OUTPUT_WEB],
                'required': False,
            },
        )
        create_channel(
            uuid=constants.UUID_CHANNEL_JOBS,
            defaults={
                'type_id': notification.JobsChannelType.id,
                'default_outputs': [OUTPUT_WEB],
                'required': False,
            },
        )
        create_channel(
            uuid=constants.UUID_CHANNEL_REMINDERS,
            defaults={
                'type_id': notification.RemindersChannelType.id,
                'required': True,
                'default_outputs': [OUTPUT_EMAIL],
            },
        )

    def _populate_menu_config(self):
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
        create_mitem(entry_id=menu.QuickFormsEntries.id, parent=creations, order=101)
        create_mitem(entry_id=Separator1Entry.id, parent=creations, order=200)
        create_mitem(entry_id=menu.EntitiesCreationEntry.id, parent=creations, order=201)

        create_mitem(entry_id=menu.RecentEntitiesEntry.id, order=1020)

    def _populate_buttons_config(self):
        if not ButtonMenuItem.objects.filter(content_type=None).exists():
            ButtonMenuItem.objects.create(
                content_type=None, button_id='', order=1,
            )

    def _populate_bricks_config(self):
        BrickDetailviewLocation.objects.multi_create(
            defaults={'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},
                {'brick': bricks.CustomFieldsBrick, 'order':  40},
                {'brick': bricks.PropertiesBrick,   'order': 450},
                {'brick': bricks.RelationsBrick,    'order': 500},

                {
                    'brick': bricks.HistoryBrick, 'order': 8,
                    'zone': BrickDetailviewLocation.RIGHT,
                },

            ],
        )

        create_bhl = BrickHomeLocation.objects.create
        create_bhl(brick_id=bricks.StatisticsBrick.id, order=8)
        create_bhl(brick_id=bricks.HistoryBrick.id,    order=10)

        create_bml = BrickMypageLocation.objects.create
        create_bml(brick_id=bricks.HistoryBrick.id, order=8, user=None)
        assert self.root is not None
        create_bml(brick_id=bricks.HistoryBrick.id, order=8, user=self.root)
