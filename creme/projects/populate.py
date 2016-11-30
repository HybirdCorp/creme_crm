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

import logging

from django.apps import apps
from django.utils.translation import ugettext as _

from creme.creme_core.blocks import (properties_block, relations_block,
        customfields_block, history_block)
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (RelationType, SearchConfigItem,
        HeaderFilter, BlockDetailviewLocation)
from creme.creme_core.utils import create_if_needed

from creme.persons import get_contact_model

from creme.activities import get_activity_model

from . import get_project_model, get_task_model
from . import blocks, constants
from .models import ProjectStatus, TaskStatus, Resource


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'activities']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_PROJECT_MANAGER).exists()
        Contact = get_contact_model()
        Activity = get_activity_model()

        Project     = get_project_model()
        ProjectTask = get_task_model()

        create_rtype = RelationType.create
        create_rtype((constants.REL_SUB_PROJECT_MANAGER, _(u'is one of the leaders of this project'), [Contact]),
                     (constants.REL_OBJ_PROJECT_MANAGER, _(u'has as leader'),                         [Project]),
                    )
        create_rtype((constants.REL_SUB_LINKED_2_PTASK, _(u'is related to the task of project'), [Activity]),
                     (constants.REL_OBJ_LINKED_2_PTASK, _(u'includes the activity'),             [ProjectTask]),
                     is_internal=True,
                    )
        create_rtype((constants.REL_SUB_PART_AS_RESOURCE, _(u'is a resource of'),  [Contact]),
                     (constants.REL_OBJ_PART_AS_RESOURCE, _(u'has as a resource'), [Activity]),
                     is_internal=True,
                    )

        # ---------------------------
        for pk, statusdesc in constants.TASK_STATUS.iteritems():
            create_if_needed(TaskStatus, {'pk': pk}, name=unicode(statusdesc.name), order=pk,
                             description=unicode(statusdesc.verbose_name), is_custom=False,
                            )

        # ---------------------------
        create_hf = HeaderFilter.create
        create_hf(pk=constants.DEFAULT_HFILTER_PROJECT,
                  model=Project,
                  name=_(u'Project view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'start_date'}),
                              (EntityCellRegularField, {'name': 'end_date'}),
                              (EntityCellRegularField, {'name': 'status'}),
                              (EntityCellRegularField, {'name': 'description'}),
                             ],
                 )

        # Used in form
        create_hf(pk='projects-hf_task', name=_(u'Task view'), model=ProjectTask,
                  cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                              (EntityCellRegularField, {'name': 'description'}),
                             ],
                 )

        # Used in form
        create_hf(pk='projects-hf_resource', name=_(u'Resource view'), model=Resource,
                  cells_desc=[(EntityCellRegularField, {'name': 'linked_contact'}),
                              (EntityCellRegularField, {'name': 'hourly_cost'}),
                             ],
                 )

        # ---------------------------
        create_searchconf = SearchConfigItem.create_if_needed
        create_searchconf(Project,     ['name', 'description', 'status__name'])
        create_searchconf(Resource,    ['linked_contact__first_name', 'linked_contact__last_name', 'hourly_cost'])
        create_searchconf(ProjectTask, ['project__name', 'duration', 'tstatus__name'])

        # ---------------------------
        if not already_populated:
            create_if_needed(ProjectStatus, {'pk': 1}, name=_(u'Invitation to tender'),  order=1, description=_(u'Response to an invitation to tender'))
            create_if_needed(ProjectStatus, {'pk': 2}, name=_(u'Initialization'),        order=2, description=_(u'The project is starting'))
            create_if_needed(ProjectStatus, {'pk': 3}, name=_(u'Preliminary phase'),     order=3, description=_(u'The project is in the process of analysis and design'))
            create_if_needed(ProjectStatus, {'pk': 4}, name=_(u'Achievement'),           order=4, description=_(u'The project is being implemented'))
            create_if_needed(ProjectStatus, {'pk': 5}, name=_(u'Tests'),                 order=5, description=_(u'The project is in the testing process (unit / integration / functional)'))
            create_if_needed(ProjectStatus, {'pk': 6}, name=_(u'User acceptance tests'), order=6, description=_(u'The project is in the user acceptance testing process'))
            create_if_needed(ProjectStatus, {'pk': 7}, name=_(u'Finished'),              order=7, description=_(u'The project is finished'))

            # ---------------------------
            create_bdl = BlockDetailviewLocation.create
            TOP   = BlockDetailviewLocation.TOP
            LEFT  = BlockDetailviewLocation.LEFT
            RIGHT = BlockDetailviewLocation.RIGHT

            create_bdl(block_id=blocks.project_tasks_block.id_, order=2,   zone=TOP,   model=Project)
            BlockDetailviewLocation.create_4_model_block(order=5,          zone=LEFT,  model=Project)
            create_bdl(block_id=blocks.project_extra_info.id_,  order=30,  zone=LEFT,  model=Project)
            create_bdl(block_id=customfields_block.id_,         order=40,  zone=LEFT,  model=Project)
            create_bdl(block_id=properties_block.id_,           order=450, zone=LEFT,  model=Project)
            create_bdl(block_id=relations_block.id_,            order=500, zone=LEFT,  model=Project)
            create_bdl(block_id=history_block.id_,              order=20,  zone=RIGHT, model=Project)

            create_bdl(block_id=blocks.task_resources_block.id_,  order=2,   zone=TOP,   model=ProjectTask)
            create_bdl(block_id=blocks.task_activities_block.id_, order=4,   zone=TOP,   model=ProjectTask)
            BlockDetailviewLocation.create_4_model_block(order=5,            zone=LEFT,  model=ProjectTask)
            create_bdl(block_id=blocks.task_extra_info.id_,       order=30,  zone=LEFT,  model=ProjectTask)
            create_bdl(block_id=customfields_block.id_,           order=40,  zone=LEFT,  model=ProjectTask)
            create_bdl(block_id=blocks.parent_tasks_block.id_,    order=50,  zone=LEFT,  model=ProjectTask)
            create_bdl(block_id=properties_block.id_,             order=450, zone=LEFT,  model=ProjectTask)
            create_bdl(block_id=relations_block.id_,              order=500, zone=LEFT,  model=ProjectTask)
            create_bdl(block_id=history_block.id_,                order=20,  zone=RIGHT, model=ProjectTask)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                for model in (Project, ProjectTask):
                    create_bdl(block_id=todos_block.id_,    order=100, zone=RIGHT, model=model)
                    create_bdl(block_id=memos_block.id_,    order=200, zone=RIGHT, model=model)
                    create_bdl(block_id=alerts_block.id_,   order=300, zone=RIGHT, model=model)
                    create_bdl(block_id=messages_block.id_, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents block on detail views')

                from creme.documents.blocks import linked_docs_block

                for model in (Project, ProjectTask):
                    create_bdl(block_id=linked_docs_block.id_, order=600, zone=RIGHT, model=model)
