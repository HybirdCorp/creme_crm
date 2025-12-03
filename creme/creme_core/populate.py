################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from django.contrib.contenttypes.models import ContentType
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
    CustomEntityType,
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
from .utils.date_period import date_period_registry

# UUIDs for instances which can be deleted
UUID_USER_ROOT = 'f53e8537-9aae-454c-adc1-a89df9563c28'
UUID_ROLE_REGULAR = 'a97a66aa-a2c0-42bf-a6d0-a4d99b604cb3'

UUID_CURRENCY_EURO              = '5777ec02-5b60-4276-9923-c833ba32df22'
UUID_CURRENCY_US_DOLLAR         = '97d30dd5-fd4d-4579-9a15-ddda78443bdd'
UUID_CURRENCY_POUND_STERLING    = '4e82eb18-f626-4928-97c1-36d3e0c04821'
UUID_CURRENCY_JAPANESE_YEN      = 'b27926fb-42c0-499e-83c5-2b8e81bba215'
UUID_CURRENCY_CHINESE_YUAN      = 'c2b6269d-0e84-40f0-8a09-29e288c076d5'
UUID_CURRENCY_SOUTH_KOREAN_WON  = '488142a2-1767-4a36-b822-b143218588a6'
UUID_CURRENCY_DINAR             = '4af52026-333a-461d-a0ec-88602204c3fb'
UUID_CURRENCY_BRAZILIAN_REAL    = 'b15f7f14-8dee-4567-b1bb-50abbb58bc19'
UUID_CURRENCY_INDIAN_RUPEE      = '664ea11e-2702-4210-9a02-3382fdb4d712'
UUID_CURRENCY_AUSTRALIAN_DOLLAR = '7a3b13bb-ded7-4fd7-9b79-4813ff0be31b'
UUID_CURRENCY_SWISS_FRANC       = 'af20cd3a-6d6b-47e1-a772-331a522ba5b0'
UUID_CURRENCY_CANADIAN_DOLLAR   = 'b6f7cef4-f4d3-48c0-8d81-7697ba2f7131'


class Populator(BasePopulator):
    RELATION_TYPES = [
        RelationType.objects.builder(
            id=constants.REL_SUB_HAS, predicate=_('owns'),
        ).symmetric(
            id=constants.REL_OBJ_HAS, predicate=_('belongs to'),
        ),
    ]
    JOBS = [
        Job(
            type=creme_jobs.sessions_cleaner_type,
            periodicity=date_period_registry.get_period('days', 1),
        ),
        Job(
            type=creme_jobs.temp_files_cleaner_type,
            periodicity=date_period_registry.get_period('days', 1),
            data={
                'delay': date_period_registry.get_period('days', 1).as_dict(),
            },
        ),
        Job(type=creme_jobs.reminder_type),
        Job(type=creme_jobs.notification_emails_sender_type),
    ]
    SANDBOXES = [
        Sandbox(
            uuid=constants.UUID_SANDBOX_SUPERUSERS,
            # 'superuser': True,
            type=sandboxes.OnlySuperusersType,
        ),
    ]
    SETTING_VALUES = [
        SettingValue(key=setting_keys.global_filters_edition_key, value=False),
        SettingValue(key=setting_keys.brick_opening_key,          value=True),
        SettingValue(key=setting_keys.brick_showempty_key,        value=True),
        SettingValue(key=setting_keys.currency_symbol_key,        value=True),
    ]
    NOTIFICATION_CHANNELS = [
        NotificationChannel(
            uuid=constants.UUID_CHANNEL_SYSTEM,
            type=notification.SystemChannelType,
            required=True,
            default_outputs=[OUTPUT_WEB],
        ),
        NotificationChannel(
            uuid=constants.UUID_CHANNEL_ADMIN,
            type=notification.AdministrationChannelType,
            default_outputs=[OUTPUT_WEB],
            required=False,
        ),
        NotificationChannel(
            uuid=constants.UUID_CHANNEL_JOBS,
            type=notification.JobsChannelType,
            default_outputs=[OUTPUT_WEB],
            required=False,
        ),
        NotificationChannel(
            uuid=constants.UUID_CHANNEL_REMINDERS,
            type=notification.RemindersChannelType,
            required=True,
            default_outputs=[OUTPUT_EMAIL],
        ),
    ]
    CURRENCIES = [
        Currency(
            uuid=UUID_CURRENCY_EURO,
            name=_('Euro'),
            local_symbol='€',
            international_symbol='EUR',
            # 'is_custom': False,
        ),
        Currency(
            uuid=UUID_CURRENCY_US_DOLLAR,
            name=_('United States dollar'),
            local_symbol='$',
            international_symbol='USD',
        ),
        Currency(
            uuid=UUID_CURRENCY_POUND_STERLING,
            name=_('Pound sterling'),
            local_symbol='£',
            international_symbol='GBP',
        ),
        Currency(
            uuid=UUID_CURRENCY_JAPANESE_YEN,
            name=_('Japanese yen'),
            local_symbol='¥',
            international_symbol='JPY',
        ),
        Currency(
            uuid=UUID_CURRENCY_CHINESE_YUAN,
            name=_('Chinese yuan'),
            local_symbol='Ұ ',
            international_symbol='CNY',
        ),
        Currency(
            uuid=UUID_CURRENCY_SOUTH_KOREAN_WON,
            name=_('South Korean won'),
            local_symbol='₩',
            international_symbol='KRW',
        ),
        Currency(
            uuid=UUID_CURRENCY_DINAR,
            name=_('Dinar'),
            local_symbol='DA',
            international_symbol='DZD',
        ),
        Currency(
            uuid=UUID_CURRENCY_BRAZILIAN_REAL,
            name=_('Brazilian real'),
            local_symbol='R$',
            international_symbol='BRL',
        ),
        Currency(
            uuid=UUID_CURRENCY_INDIAN_RUPEE,
            name=_('Indian rupee'),
            local_symbol='₹',
            international_symbol='INR',
        ),
        Currency(
            uuid=UUID_CURRENCY_AUSTRALIAN_DOLLAR,
            name=_('Australian dollar'),
            local_symbol='AU$',
            international_symbol='AUD',
        ),
        Currency(
            uuid=UUID_CURRENCY_SWISS_FRANC,
            name=_('Swiss franc'),
            local_symbol=_('CHF'),
            international_symbol='CHF',
        ),
        Currency(
            uuid=UUID_CURRENCY_CANADIAN_DOLLAR,
            name=_('Canadian dollar'),
            local_symbol='CA$',
            international_symbol='CAD',
        ),
    ]

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
        self._populate_custom_entity_types()
        self._populate_currencies()

        self._fix_roles()  # To be deleted in next major version

        if settings.TESTS_ON:
            from .tests import fake_populate
            fake_populate.populate()

    def _first_populate(self):
        self._populate_root()
        super()._first_populate()
        self._populate_roles()
        self._populate_languages()
        self._populate_vats()

    # NB: creme_registry cannot be used in classical migrations, so we are
    #     obliged to fill the new field userRole.listable_ctypes here.
    def _fix_roles(self):
        from .registry import creme_registry

        get_ct = ContentType.objects.get_for_model

        for role in UserRole.objects.filter(extra_data__listablemigr__isnull=True):
            allowed_apps = role.allowed_apps
            role.listable_ctypes.set([
                get_ct(model)
                for model in creme_registry.iter_entity_models()
                if model._meta.app_label in allowed_apps
            ])
            # TODO: remove this key in next major version
            role.extra_data['listablemigr'] = True
            role.save()

    def _populate_root(self):
        login = constants.ROOT_USERNAME
        password = constants.ROOT_PASSWORD
        self.root = get_user_model().objects.create_superuser(
            uuid=UUID_USER_ROOT,
            username=login, password=password,
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
            uuid=UUID_ROLE_REGULAR,
            allowed_apps=[
                app.label for app in creme_app_configs() if app.credentials & CRED_REGULAR
            ],
            creatable_models=entity_models,
            listable_models=entity_models,
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

    def _populate_custom_entity_types(self):
        create_type = CustomEntityType.objects.get_or_create

        for idx in CustomEntityType.custom_classes.keys():
            create_type(
                id=idx,
                defaults={
                    'name':        f'Placeholder #{idx}',
                    'plural_name': f'Placeholders #{idx}',
                },
            )

    def _populate_currencies(self):
        self._save_minions(self.CURRENCIES)

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

    # def _populate_relation_types(self):
    #     RelationType.objects.smart_update_or_create(
    #         (constants.REL_SUB_HAS, _('owns')),
    #         (constants.REL_OBJ_HAS, _('belongs to')),
    #     )

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

        # create_mitem(entry_id=menu.RecentEntitiesEntry.id, order=1020)
        create_mitem(entry_id=menu.QuickAccessEntry.id, order=1020)

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
        create_bhl(brick_id=bricks.RecentEntitiesBrick.id, order=1)
        create_bhl(brick_id=bricks.StatisticsBrick.id,     order=8)
        create_bhl(brick_id=bricks.HistoryBrick.id,        order=10)

        create_bml = BrickMypageLocation.objects.create
        create_bml(brick_id=bricks.RecentEntitiesBrick.id, order=1, user=None)
        create_bml(brick_id=bricks.PinnedEntitiesBrick.id, order=2, user=None)
        create_bml(brick_id=bricks.HistoryBrick.id,        order=8, user=None)

        root = self.root
        assert root is not None
        create_bml(brick_id=bricks.RecentEntitiesBrick.id, order=1, user=root)
        create_bml(brick_id=bricks.PinnedEntitiesBrick.id, order=2, user=root)
        create_bml(brick_id=bricks.HistoryBrick.id,        order=8, user=root)
