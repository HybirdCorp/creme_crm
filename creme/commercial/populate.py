# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, CremePropertyType, SettingValue,
        Job, BrickDetailviewLocation, SearchConfigItem, ButtonMenuItem, HeaderFilter)
from creme.creme_core.utils import create_if_needed
from creme.creme_core.utils.date_period import date_period_registry

from creme import persons

from creme import commercial
from . import bricks, buttons, constants, creme_jobs, setting_keys
from .models import MarketSegment, ActType

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_SOLD_BY).exists()

        Act = commercial.get_act_model()
        ActObjectivePattern = commercial.get_pattern_model()
        Strategy = commercial.get_strategy_model()
        Contact = persons.get_contact_model()
        Organisation = persons.get_organisation_model()

        RelationType.create((constants.REL_SUB_SOLD_BY,       _('has sold')),
                            (constants.REL_OBJ_SOLD_BY,       _('has been sold by')))
        RelationType.create((constants.REL_SUB_COMPLETE_GOAL, _('completes a goal of the commercial action')),
                            (constants.REL_OBJ_COMPLETE_GOAL, _('is completed thanks to'), [Act]))

        # ---------------------------
        CremePropertyType.create(constants.PROP_IS_A_SALESMAN, _('is a salesman'), [Contact])

        # ---------------------------
        MarketSegment.objects.get_or_create(property_type=None,
                                            defaults={'name': _('All the organisations')},
                                           )

        # ---------------------------
        for i, title in enumerate([_('Phone calls'), _('Show'), _('Demo')], start=1):
            create_if_needed(ActType, {'pk': i}, title=title, is_custom=False)

        # ---------------------------
        create_hf = HeaderFilter.create
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
                             ]
                 )

        # ---------------------------
        create_searchconf = SearchConfigItem.create_if_needed
        create_searchconf(Act, ['name', 'expected_sales', 'cost', 'goal'])
        create_searchconf(Strategy, ['name'])
        create_searchconf(ActObjectivePattern, [], disabled=True)

        # ---------------------------
        SettingValue.objects.get_or_create(key_id=setting_keys.orga_approaches_key.id, defaults={'value': True})

        # ---------------------------
        Job.objects.get_or_create(type_id=creme_jobs.com_approaches_emails_send_type.id,
                                  defaults={'language':    settings.LANGUAGE_CODE,
                                            'periodicity': date_period_registry.get_period('days', 1),
                                            'status':      Job.STATUS_OK,
                                           }
                                 )

        # ---------------------------
        if not already_populated:
            ButtonMenuItem.create_if_needed(pk='commercial-complete_goal_button',
                                            model=None, button=buttons.CompleteGoalButton, order=60,
                                           )

            create_bdl           = BrickDetailviewLocation.objects.create_if_needed
            create_bdl_for_model = BrickDetailviewLocation.objects.create_for_model_brick
            TOP   = BrickDetailviewLocation.TOP
            RIGHT = BrickDetailviewLocation.RIGHT
            LEFT  = BrickDetailviewLocation.LEFT

            create_bdl(brick=bricks.ApproachesBrick, order=10, zone=RIGHT)
            create_bdl(brick=bricks.ApproachesBrick, order=10, zone=RIGHT, model=Contact)
            create_bdl(brick=bricks.ApproachesBrick, order=10, zone=RIGHT, model=Organisation)

            create_bdl_for_model(                              order=5,   zone=LEFT,  model=Act)
            create_bdl(brick=bricks.ActObjectivesBrick,        order=10,  zone=LEFT,  model=Act)
            create_bdl(brick=bricks.RelatedOpportunitiesBrick, order=20,  zone=LEFT,  model=Act)
            create_bdl(brick=core_bricks.CustomFieldsBrick,    order=40,  zone=LEFT,  model=Act)
            create_bdl(brick=core_bricks.PropertiesBrick,      order=450, zone=LEFT,  model=Act)
            create_bdl(brick=core_bricks.RelationsBrick,       order=500, zone=LEFT,  model=Act)
            create_bdl(brick=core_bricks.HistoryBrick,         order=20,  zone=RIGHT, model=Act)

            create_bdl(brick=bricks.PatternComponentsBrick, order=10,  zone=TOP,   model=ActObjectivePattern)
            create_bdl_for_model(                           order=5,   zone=LEFT,  model=ActObjectivePattern)
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT,  model=ActObjectivePattern)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT,  model=ActObjectivePattern)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT,  model=ActObjectivePattern)
            create_bdl(brick=core_bricks.HistoryBrick,      order=20,  zone=RIGHT, model=ActObjectivePattern)

            create_bdl(brick=bricks.SegmentDescriptionsBrick, order=10,  zone=TOP,   model=Strategy)
            create_bdl_for_model(                             order=5,   zone=LEFT,  model=Strategy)
            create_bdl(brick=core_bricks.CustomFieldsBrick,   order=40,  zone=LEFT,  model=Strategy)
            create_bdl(brick=bricks.EvaluatedOrgasBrick,      order=50,  zone=LEFT,  model=Strategy)
            create_bdl(brick=bricks.AssetsBrick,              order=60,  zone=LEFT,  model=Strategy)
            create_bdl(brick=bricks.CharmsBrick,              order=70,  zone=LEFT,  model=Strategy)
            create_bdl(brick=core_bricks.PropertiesBrick,     order=450, zone=LEFT,  model=Strategy)
            create_bdl(brick=core_bricks.RelationsBrick,      order=500, zone=LEFT,  model=Strategy)
            create_bdl(brick=core_bricks.HistoryBrick,        order=20,  zone=RIGHT, model=Strategy)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants import bricks as assistants_bricks

                for model in (Act, ActObjectivePattern, Strategy):
                    create_bdl(brick=assistants_bricks.TodosBrick,        order=100, zone=RIGHT, model=model)
                    create_bdl(brick=assistants_bricks.MemosBrick,        order=200, zone=RIGHT, model=model)
                    create_bdl(brick=assistants_bricks.AlertsBrick,       order=300, zone=RIGHT, model=model)
                    create_bdl(brick=assistants_bricks.UserMessagesBrick, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info("Documents app is installed => we use the documents blocks on Strategy's detail views")

                from creme.documents.bricks import LinkedDocsBrick

                for model in (Act, ActObjectivePattern, Strategy):
                    create_bdl(brick=LinkedDocsBrick, order=600, zone=RIGHT, model=model)
