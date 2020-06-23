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
        create_hf(pk=constants.DEFAULT_HFILTER_ACT, model=Act,
                  name=_('Com Action view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'expected_sales'}),
                              (EntityCellRegularField, {'name': 'due_date'}),
                             ],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_STRATEGY, model=Strategy,
                  name=_('Strategy view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_PATTERN, model=ActObjectivePattern,
                  name=_('Objective pattern view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
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

            create_bdl           = BrickDetailviewLocation.objects.create_if_needed
            create_bdl_for_model = BrickDetailviewLocation.objects.create_for_model_brick
            TOP   = BrickDetailviewLocation.TOP
            RIGHT = BrickDetailviewLocation.RIGHT
            LEFT  = BrickDetailviewLocation.LEFT

            create_bdl(brick=bricks.ApproachesBrick, order=10, zone=RIGHT)
            create_bdl(brick=bricks.ApproachesBrick, order=10, zone=RIGHT, model=Contact)
            create_bdl(brick=bricks.ApproachesBrick, order=10, zone=RIGHT, model=Organisation)

            def create_multi_bdl(model, info):
                for brick, order, zone in info:
                    if brick == 'model':
                        create_bdl_for_model(order=order, zone=zone, model=model)
                    else:
                        create_bdl(brick=brick, order=order, zone=zone, model=model)

            create_multi_bdl(
                Act,
                [
                    ('model',                            5, LEFT),
                    (bricks.ActObjectivesBrick,         10, LEFT),
                    (bricks.RelatedOpportunitiesBrick,  20, LEFT),
                    (core_bricks.CustomFieldsBrick,     40, LEFT),
                    (core_bricks.PropertiesBrick,      450, LEFT),
                    (core_bricks.RelationsBrick,       500, LEFT),
                    (core_bricks.HistoryBrick,          20, RIGHT),
                ]
            )
            create_multi_bdl(
                ActObjectivePattern,
                [
                    (bricks.PatternComponentsBrick,  10, TOP),
                    ('model',                         5, LEFT),
                    (core_bricks.CustomFieldsBrick,  40, LEFT),
                    (core_bricks.PropertiesBrick,   450, LEFT),
                    (core_bricks.RelationsBrick,    500, LEFT),
                    (core_bricks.HistoryBrick,       20, RIGHT),
                ]
            )
            create_multi_bdl(
                Strategy,
                [
                    (bricks.SegmentDescriptionsBrick,  10, TOP),
                    ('model',                           5, LEFT),
                    (core_bricks.CustomFieldsBrick,    40, LEFT),
                    (bricks.EvaluatedOrgasBrick,       50, LEFT),
                    (bricks.AssetsBrick,               60, LEFT),
                    (bricks.CharmsBrick,               70, LEFT),
                    (core_bricks.PropertiesBrick,     450, LEFT),
                    (core_bricks.RelationsBrick,      500, LEFT),
                    (core_bricks.HistoryBrick,         20, RIGHT),
                ]
            )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed '
                    '=> we use the assistants blocks on detail views'
                )

                from creme.assistants import bricks as assistants_bricks

                for model in (Act, ActObjectivePattern, Strategy):
                    create_multi_bdl(
                        model,
                        [
                            (assistants_bricks.TodosBrick,        100, RIGHT),
                            (assistants_bricks.MemosBrick,        200, RIGHT),
                            (assistants_bricks.AlertsBrick,       300, RIGHT),
                            (assistants_bricks.UserMessagesBrick, 400, RIGHT),
                        ]
                    )

            if apps.is_installed('creme.documents'):
                # logger.info("Documents app is installed
                # => we use the documents blocks on Strategy's detail views")

                from creme.documents.bricks import LinkedDocsBrick

                for model in (Act, ActObjectivePattern, Strategy):
                    create_bdl(brick=LinkedDocsBrick, order=600, zone=RIGHT, model=model)
