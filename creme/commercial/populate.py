# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from django.utils.translation import ugettext as _

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, CremePropertyType, SettingValue,
        Job, BlockDetailviewLocation, SearchConfigItem, ButtonMenuItem, HeaderFilter)
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

        RelationType.create((constants.REL_SUB_SOLD_BY,       _(u'has sold')),
                            (constants.REL_OBJ_SOLD_BY,       _(u'has been sold by')))
        RelationType.create((constants.REL_SUB_COMPLETE_GOAL, _(u'completes a goal of the commercial action')),
                            (constants.REL_OBJ_COMPLETE_GOAL, _(u'is completed thanks to'), [Act]))

        # ---------------------------
        CremePropertyType.create(constants.PROP_IS_A_SALESMAN, _(u'is a salesman'), [Contact])

        # ---------------------------
        MarketSegment.objects.get_or_create(property_type=None,
                                            defaults={'name': _(u'All the organisations')},
                                           )

        # ---------------------------
        for i, title in enumerate([_(u'Phone calls'), _(u'Show'), _(u'Demo')], start=1):
            create_if_needed(ActType, {'pk': i}, title=title, is_custom=False)

        # ---------------------------
        create_hf = HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_ACT, model=Act,
                  name=_(u'Com Action view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'expected_sales'}),
                              (EntityCellRegularField, {'name': 'due_date'}),
                             ],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_STRATEGY, model=Strategy,
                  name=_(u"Strategy view"),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'})],
                 )
        create_hf(pk=constants.DEFAULT_HFILTER_PATTERN, model=ActObjectivePattern,
                  name=_(u"Objective pattern view"),
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
                                            model=None, button=buttons.complete_goal_button, order=60,
                                           )

            create_bdl = BlockDetailviewLocation.create
            TOP = BlockDetailviewLocation.TOP
            RIGHT = BlockDetailviewLocation.RIGHT
            LEFT = BlockDetailviewLocation.LEFT

            create_bdl(block_id=bricks.ApproachesBrick.id_, order=10, zone=RIGHT)
            create_bdl(block_id=bricks.ApproachesBrick.id_, order=10, zone=RIGHT, model=Contact)
            create_bdl(block_id=bricks.ApproachesBrick.id_, order=10, zone=RIGHT, model=Organisation)

            BlockDetailviewLocation.create_4_model_brick(order=5,                zone=LEFT,  model=Act)
            create_bdl(block_id=bricks.ActObjectivesBrick.id_,        order=10,  zone=LEFT,  model=Act)
            create_bdl(block_id=bricks.RelatedOpportunitiesBrick.id_, order=20,  zone=LEFT,  model=Act)
            create_bdl(block_id=core_bricks.CustomFieldsBrick.id_,    order=40,  zone=LEFT,  model=Act)
            create_bdl(block_id=core_bricks.PropertiesBrick.id_,      order=450, zone=LEFT,  model=Act)
            create_bdl(block_id=core_bricks.RelationsBrick.id_,       order=500, zone=LEFT,  model=Act)
            create_bdl(block_id=core_bricks.HistoryBrick.id_,         order=20,  zone=RIGHT, model=Act)

            create_bdl(block_id=bricks.PatternComponentsBrick.id_, order=10,  zone=TOP,   model=ActObjectivePattern)
            BlockDetailviewLocation.create_4_model_brick(order=5,             zone=LEFT,  model=ActObjectivePattern)
            create_bdl(block_id=core_bricks.CustomFieldsBrick.id_, order=40,  zone=LEFT,  model=ActObjectivePattern)
            create_bdl(block_id=core_bricks.PropertiesBrick.id_,   order=450, zone=LEFT,  model=ActObjectivePattern)
            create_bdl(block_id=core_bricks.RelationsBrick.id_,    order=500, zone=LEFT,  model=ActObjectivePattern)
            create_bdl(block_id=core_bricks.HistoryBrick.id_,      order=20,  zone=RIGHT, model=ActObjectivePattern)

            create_bdl(block_id=bricks.SegmentDescriptionsBrick.id_, order=10,  zone=TOP,   model=Strategy)
            BlockDetailviewLocation.create_4_model_brick(order=5,               zone=LEFT,  model=Strategy)
            create_bdl(block_id=core_bricks.CustomFieldsBrick.id_,   order=40,  zone=LEFT,  model=Strategy)
            create_bdl(block_id=bricks.EvaluatedOrgasBrick.id_,      order=50,  zone=LEFT,  model=Strategy)
            create_bdl(block_id=bricks.AssetsBrick.id_,              order=60,  zone=LEFT,  model=Strategy)
            create_bdl(block_id=bricks.CharmsBrick.id_,              order=70,  zone=LEFT,  model=Strategy)
            create_bdl(block_id=core_bricks.PropertiesBrick.id_,     order=450, zone=LEFT,  model=Strategy)
            create_bdl(block_id=core_bricks.RelationsBrick.id_,      order=500, zone=LEFT,  model=Strategy)
            create_bdl(block_id=core_bricks.HistoryBrick.id_,        order=20,  zone=RIGHT, model=Strategy)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants import bricks as assistants_bricks

                for model in (Act, ActObjectivePattern, Strategy):
                    create_bdl(block_id=assistants_bricks.TodosBrick.id_,        order=100, zone=RIGHT, model=model)
                    create_bdl(block_id=assistants_bricks.MemosBrick.id_,        order=200, zone=RIGHT, model=model)
                    create_bdl(block_id=assistants_bricks.AlertsBrick.id_,       order=300, zone=RIGHT, model=model)
                    create_bdl(block_id=assistants_bricks.UserMessagesBrick.id_, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info("Documents app is installed => we use the documents blocks on Strategy's detail views")

                from creme.documents.bricks import LinkedDocsBrick

                for model in (Act, ActObjectivePattern, Strategy):
                    create_bdl(block_id=LinkedDocsBrick.id_, order=600, zone=RIGHT, model=model)
