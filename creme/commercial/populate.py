# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from creme import commercial, persons, products
from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    ButtonMenuItem,
    CremePropertyType,
    HeaderFilter,
    Job,
    RelationType,
    SearchConfigItem,
    SettingValue,
)
from creme.creme_core.registry import creme_registry
from creme.creme_core.utils import create_if_needed
from creme.creme_core.utils.date_period import date_period_registry

from . import bricks, buttons, constants, creme_jobs, setting_keys
from .models import ActType, MarketSegment

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'products']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_SOLD).exists()

        Act = commercial.get_act_model()
        ActObjectivePattern = commercial.get_pattern_model()
        Strategy = commercial.get_strategy_model()
        Contact = persons.get_contact_model()
        Organisation = persons.get_organisation_model()
        Product = products.get_product_model()
        Service = products.get_service_model()

        RelationType.create(
            (constants.REL_SUB_SOLD, _('has sold'),         [Contact, Organisation]),
            (constants.REL_OBJ_SOLD, _('has been sold by'), [Product, Service]),
        )

        complete_goal_models = {*creme_registry.iter_entity_models()}
        complete_goal_models.discard(Strategy)
        if apps.is_installed('creme.billing'):
            from creme import billing
            from creme.billing.registry import lines_registry

            complete_goal_models.discard(billing.get_credit_note_model())
            complete_goal_models.discard(billing.get_template_base_model())
            complete_goal_models.difference_update(lines_registry)

        RelationType.create(
            (
                constants.REL_SUB_COMPLETE_GOAL,
                _('completes a goal of the commercial action'),
                complete_goal_models,
            ),
            (
                constants.REL_OBJ_COMPLETE_GOAL,
                _('is completed thanks to'),
                [Act],
            ),
        )

        # ---------------------------
        CremePropertyType.create(constants.PROP_IS_A_SALESMAN, _('is a salesman'), [Contact])

        # ---------------------------
        MarketSegment.objects.get_or_create(
            property_type=None,
            defaults={'name': _('All the organisations')},
        )

        # ---------------------------
        for i, title in enumerate([_('Phone calls'), _('Show'), _('Demo')], start=1):
            create_if_needed(ActType, {'pk': i}, title=title, is_custom=False)

        # ---------------------------
        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_ACT, model=Act,
            name=_('Com Action view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'expected_sales'}),
                (EntityCellRegularField, {'name': 'due_date'}),
            ],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_STRATEGY, model=Strategy,
            name=_('Strategy view'),
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )
        create_hf(
            pk=constants.DEFAULT_HFILTER_PATTERN, model=ActObjectivePattern,
            name=_('Objective pattern view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'segment'}),
            ],
        )

        # ---------------------------
        create_searchconf = SearchConfigItem.objects.create_if_needed
        create_searchconf(Act, ['name', 'expected_sales', 'cost', 'goal'])
        create_searchconf(Strategy, ['name'])
        create_searchconf(ActObjectivePattern, [], disabled=True)

        # ---------------------------
        SettingValue.objects.get_or_create(
            key_id=setting_keys.orga_approaches_key.id,
            defaults={'value': True},
        )

        # ---------------------------
        Job.objects.get_or_create(
            type_id=creme_jobs.com_approaches_emails_send_type.id,
            defaults={
                'language':    settings.LANGUAGE_CODE,
                'periodicity': date_period_registry.get_period('days', 1),
                'status':      Job.STATUS_OK,
            },
        )

        # ---------------------------
        if not already_populated:
            ButtonMenuItem.objects.create_if_needed(
                pk='commercial-complete_goal_button',
                button=buttons.CompleteGoalButton, order=60,
            )

            TOP   = BrickDetailviewLocation.TOP
            RIGHT = BrickDetailviewLocation.RIGHT
            LEFT  = BrickDetailviewLocation.LEFT

            BrickDetailviewLocation.objects.multi_create(
                defaults={'brick': bricks.ApproachesBrick, 'order': 10, 'zone': RIGHT},
                data=[
                    {},  # default configuration
                    {'model': Contact},
                    {'model': Organisation},
                ]
            )

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Act, 'zone': LEFT},
                data=[
                    {'order': 5},  # generic information brick
                    {'brick': bricks.ActObjectivesBrick,        'order': 10},
                    {'brick': bricks.RelatedOpportunitiesBrick, 'order': 20},
                    {'brick': core_bricks.CustomFieldsBrick,    'order': 40},
                    {'brick': core_bricks.PropertiesBrick,      'order': 450},
                    {'brick': core_bricks.RelationsBrick,       'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': ActObjectivePattern, 'zone': LEFT},
                data=[
                    {'brick': bricks.PatternComponentsBrick, 'order': 10, 'zone': TOP},

                    {'order': 5},
                    {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Strategy, 'zone': LEFT},
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

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed '
                    '=> we use the assistants blocks on detail views'
                )

                from creme.assistants import bricks as a_bricks

                for model in (Act, ActObjectivePattern, Strategy):
                    BrickDetailviewLocation.objects.multi_create(
                        defaults={'model': model, 'zone': RIGHT},
                        data=[
                            {'brick': a_bricks.TodosBrick,        'order': 100},
                            {'brick': a_bricks.MemosBrick,        'order': 200},
                            {'brick': a_bricks.AlertsBrick,       'order': 300},
                            {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                        ],
                    )

            if apps.is_installed('creme.documents'):
                # logger.info("Documents app is installed
                # => we use the documents blocks on Strategy's detail views")

                from creme.documents.bricks import LinkedDocsBrick

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'brick': LinkedDocsBrick, 'order': 600, 'zone': RIGHT},
                    data=[
                        {'model': Act},
                        {'model': ActObjectivePattern},
                        {'model': Strategy},
                    ],
                )
