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

import logging

from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext as _

import creme.creme_core.bricks as core_bricks
from creme import commercial, persons, products
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    ButtonMenuItem,
    CremePropertyType,
    CustomFormConfigItem,
    HeaderFilter,
    Job,
    MenuConfigItem,
    RelationType,
    SearchConfigItem,
    SettingValue,
)
from creme.creme_core.registry import creme_registry
# from creme.creme_core.utils import create_if_needed
from creme.creme_core.utils.date_period import date_period_registry

from . import (
    bricks,
    buttons,
    constants,
    creme_jobs,
    custom_forms,
    menu,
    setting_keys,
)
from .models import ActType, MarketSegment

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'products']

    SEARCH = {
        'ACT': ['name', 'expected_sales', 'cost', 'goal'],
        'STRATEGY': ['name'],
        'PATTERN': [],
    }
    ACT_TYPES = [
        ActType(
            uuid='e443e7f0-df22-4f4c-9bc8-7f718867e3d1',
            title=_('Phone calls'), is_custom=False
        ),
        ActType(
            uuid='2937497e-05b2-4790-8fa9-7f2a05dbfee0',
            title=_('Show'), is_custom=False
        ),
        ActType(
            uuid='4cfcefd1-3140-4e9f-a6f5-ce7de1e08f51',
            title=_('Demo'), is_custom=False,
        ),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.Contact      = persons.get_contact_model()
        self.Organisation = persons.get_organisation_model()

        self.Product = products.get_product_model()
        self.Service = products.get_service_model()

        self.Act                 = commercial.get_act_model()
        self.ActObjectivePattern = commercial.get_pattern_model()
        self.Strategy            = commercial.get_strategy_model()

    def _already_populated(self):
        return RelationType.objects.filter(pk=constants.REL_SUB_SOLD).exists()

    def _populate(self):
        super()._populate()
        self._populate_market_segments()
        self._populate_act_types()

    def _populate_market_segments(self):
        MarketSegment.objects.get_or_create(
            property_type=None,
            defaults={'name': _('All the organisations')},
        )

    def _populate_act_types(self):
        # for i, title in enumerate([_('Phone calls'), _('Show'), _('Demo')], start=1):
        #     create_if_needed(ActType, {'pk': i}, title=title, is_custom=False)
        self._save_minions(self.ACT_TYPES)

    def _populate_relation_types(self):
        RelationType.objects.smart_update_or_create(
            (constants.REL_SUB_SOLD, _('has sold'),         [self.Contact, self.Organisation]),
            (constants.REL_OBJ_SOLD, _('has been sold by'), [self.Product, self.Service]),
        )

        complete_goal_models = {*creme_registry.iter_entity_models()}
        complete_goal_models.discard(self.Strategy)
        if apps.is_installed('creme.billing'):
            from creme import billing
            from creme.billing.registry import lines_registry

            complete_goal_models.discard(billing.get_credit_note_model())
            complete_goal_models.discard(billing.get_template_base_model())
            complete_goal_models.difference_update(lines_registry)

        RelationType.objects.smart_update_or_create(
            (
                constants.REL_SUB_COMPLETE_GOAL,
                _('completes a goal of the commercial action'),
                complete_goal_models,
            ),
            (
                constants.REL_OBJ_COMPLETE_GOAL,
                _('is completed thanks to'),
                [self.Act],
            ),
        )

    def _populate_property_types(self):
        CremePropertyType.objects.smart_update_or_create(
            # str_pk=constants.PROP_IS_A_SALESMAN,
            uuid=constants.UUID_PROP_IS_A_SALESMAN,
            app_label='commercial',
            text=_('is a salesman'),
            subject_ctypes=[self.Contact],
        )

    def _populate_header_filters_for_act(self):
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_ACT, model=self.Act,
            name=_('Com Action view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'expected_sales'}),
                (EntityCellRegularField, {'name': 'due_date'}),
            ],
        )

    def _populate_header_filters_for_strategy(self):
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_STRATEGY, model=self.Strategy,
            name=_('Strategy view'),
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

    def _populate_header_filters_for_pattern(self):
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_PATTERN, model=self.ActObjectivePattern,
            name=_('Objective pattern view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'segment'}),
            ],
        )

    def _populate_header_filters(self):
        self._populate_header_filters_for_act()
        self._populate_header_filters_for_strategy()
        self._populate_header_filters_for_pattern()

    def _populate_jobs(self):
        Job.objects.get_or_create(
            type_id=creme_jobs.com_approaches_emails_send_type.id,
            defaults={
                'language':    settings.LANGUAGE_CODE,
                'periodicity': date_period_registry.get_period('days', 1),
                'status':      Job.STATUS_OK,
                # The CommercialApproach field for Activities' CustomForms is not
                # in the default configuration, so a enabled job would be annoying.
                'enabled': False,
            },
        )

    def _populate_custom_forms(self):
        create_cform = CustomFormConfigItem.objects.create_if_needed
        create_cform(descriptor=custom_forms.ACT_CREATION_CFORM)
        create_cform(descriptor=custom_forms.ACT_EDITION_CFORM)
        create_cform(descriptor=custom_forms.PATTERN_CREATION_CFORM)
        create_cform(descriptor=custom_forms.PATTERN_EDITION_CFORM)
        create_cform(descriptor=custom_forms.STRATEGY_CREATION_CFORM)
        create_cform(descriptor=custom_forms.STRATEGY_EDITION_CFORM)

    def _populate_search_config(self):
        def create_sci(model, key):
            fields = self.SEARCH[key]
            SearchConfigItem.objects.create_if_needed(
                model=model, fields=fields, disabled=not bool(fields),
            )

        create_sci(model=self.Act,                 key='ACT')
        create_sci(model=self.Strategy,            key='STRATEGY')
        create_sci(model=self.ActObjectivePattern, key='PATTERN')

    def _populate_setting_values(self):
        SettingValue.objects.get_or_create(
            key_id=setting_keys.orga_approaches_key.id,
            defaults={'value': True},
        )

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Commercial')},
            defaults={'order': 30},
        )[0]

        create_mitem = MenuConfigItem.objects.create
        create_mitem(entry_id=menu.ActsEntry.id,       order=50, parent=menu_container)
        create_mitem(entry_id=menu.StrategiesEntry.id, order=55, parent=menu_container)
        create_mitem(entry_id=menu.SegmentsEntry.id,   order=60, parent=menu_container)
        create_mitem(entry_id=menu.PatternsEntry.id,   order=70, parent=menu_container)

        directory_entry = MenuConfigItem.objects.filter(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Directory')},
        ).first()
        if directory_entry is not None:
            create_mitem(entry_id=menu.SalesmenEntry.id, order=100, parent=directory_entry)

        creations_entry = MenuConfigItem.objects.filter(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('+ Creation')},
        ).first()
        if creations_entry is not None:
            create_mitem(entry_id=menu.ActCreationEntry.id, order=40, parent=creations_entry)

    def _populate_buttons_config(self):
        ButtonMenuItem.objects.create_if_needed(
            button=buttons.CompleteGoalButton, order=60,
        )

    def _populate_bricks_config_for_act(self):
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.Act, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'order': 5},  # generic information brick
                {'brick': bricks.ActObjectivesBrick,        'order':  10},
                {'brick': bricks.RelatedOpportunitiesBrick, 'order':  20},
                {'brick': core_bricks.CustomFieldsBrick,    'order':  40},
                {'brick': core_bricks.PropertiesBrick,      'order': 450},
                {'brick': core_bricks.RelationsBrick,       'order': 500},

                {
                    'brick': core_bricks.HistoryBrick, 'order': 20,
                    'zone': BrickDetailviewLocation.RIGHT,
                },
            ],
        )

    def _populate_bricks_config_for_pattern(self):
        TOP = BrickDetailviewLocation.TOP
        RIGHT = BrickDetailviewLocation.RIGHT
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.ActObjectivePattern, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'brick': bricks.PatternComponentsBrick, 'order': 10, 'zone': TOP},

                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ],
        )

    def _populate_bricks_config_for_strategy(self):
        TOP = BrickDetailviewLocation.TOP
        RIGHT = BrickDetailviewLocation.RIGHT
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.Strategy, 'zone': BrickDetailviewLocation.LEFT},
            data=[
                {'brick': bricks.SegmentDescriptionsBrick, 'order': 10, 'zone': TOP},

                {'order': 5},
                {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                {'brick': bricks.EvaluatedOrgasBrick,    'order':  50},
                {'brick': bricks.AssetsBrick,            'order':  60},
                {'brick': bricks.CharmsBrick,            'order':  70},
                {'brick': core_bricks.PropertiesBrick,   'order': 450},
                {'brick': core_bricks.RelationsBrick,    'order': 500},

                {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
            ],
        )

    def _populate_bricks_config_for_assistants(self):
        logger.info(
            'Assistants app is installed '
            '=> we use the assistants blocks on detail views'
        )

        import creme.assistants.bricks as a_bricks

        for model in (self.Act, self.ActObjectivePattern, self.Strategy):
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': model, 'zone': BrickDetailviewLocation.RIGHT},
                data=[
                    {'brick': a_bricks.TodosBrick,        'order': 100},
                    {'brick': a_bricks.MemosBrick,        'order': 200},
                    {'brick': a_bricks.AlertsBrick,       'order': 300},
                    {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                ],
            )

    def _populate_bricks_config_for_documents(self):
        # logger.info("Documents app is installed
        # => we use the documents blocks on Strategy's detail views")

        from creme.documents.bricks import LinkedDocsBrick

        BrickDetailviewLocation.objects.multi_create(
            defaults={
                'brick': LinkedDocsBrick, 'order': 600,
                'zone': BrickDetailviewLocation.RIGHT,
            },
            data=[
                {'model': self.Act},
                {'model': self.ActObjectivePattern},
                {'model': self.Strategy},
            ],
        )

    def _populate_bricks_config(self):
        self._populate_bricks_config_for_act()
        self._populate_bricks_config_for_pattern()
        self._populate_bricks_config_for_strategy()

        if apps.is_installed('creme.assistants'):
            self._populate_bricks_config_for_assistants()

        if apps.is_installed('creme.documents'):
            self._populate_bricks_config_for_documents()
