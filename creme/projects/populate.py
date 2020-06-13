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
from django.utils.translation import gettext as _

from creme.activities import get_activity_model
from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    HeaderFilter,
    RelationType,
    SearchConfigItem,
)
from creme.creme_core.utils import create_if_needed
from creme.persons import get_contact_model

from . import bricks, constants, get_project_model, get_task_model
from .models import ProjectStatus, Resource, TaskStatus

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
        create_rtype(
            (constants.REL_SUB_PROJECT_MANAGER, _('is one of the leaders of this project'), [Contact]),
            (constants.REL_OBJ_PROJECT_MANAGER, _('has as leader'),                         [Project]),
        )
        create_rtype(
            (constants.REL_SUB_LINKED_2_PTASK, _('is related to the task of project'), [Activity]),
            (constants.REL_OBJ_LINKED_2_PTASK, _('includes the activity'),             [ProjectTask]),
            is_internal=True,
            minimal_display=(False, True),
        )
        create_rtype(
            (constants.REL_SUB_PART_AS_RESOURCE, _('is a resource of'),  [Contact]),
            (constants.REL_OBJ_PART_AS_RESOURCE, _('has as a resource'), [Activity]),
            is_internal=True,
        )

        # ---------------------------
        for pk, statusdesc in constants.TASK_STATUS.items():
            create_if_needed(TaskStatus, {'pk': pk}, name=str(statusdesc.name), order=pk,
                             description=str(statusdesc.verbose_name), is_custom=False,
                            )

        # ---------------------------
        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(pk=constants.DEFAULT_HFILTER_PROJECT,
                  model=Project,
                  name=_('Project view'),
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'start_date'}),
                              (EntityCellRegularField, {'name': 'end_date'}),
                              (EntityCellRegularField, {'name': 'status'}),
                              (EntityCellRegularField, {'name': 'description'}),
                             ],
                 )

        # Used in form
        create_hf(pk='projects-hf_task', name=_('Task view'), model=ProjectTask,
                  cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                              (EntityCellRegularField, {'name': 'description'}),
                             ],
                 )

        # Used in form
        create_hf(pk='projects-hf_resource', name=_('Resource view'), model=Resource,
                  cells_desc=[(EntityCellRegularField, {'name': 'linked_contact'}),
                              (EntityCellRegularField, {'name': 'hourly_cost'}),
                             ],
                 )

        # ---------------------------
        create_searchconf = SearchConfigItem.objects.create_if_needed
        create_searchconf(Project,     ['name', 'description', 'status__name'])
        create_searchconf(Resource,    ['linked_contact__last_name', 'linked_contact__first_name', 'hourly_cost'])
        create_searchconf(ProjectTask, ['linked_project__name', 'duration', 'tstatus__name'])

        # ---------------------------
        if not already_populated:
            create_if_needed(ProjectStatus, {'pk': 1}, name=_('Invitation to tender'),  order=1, description=_('Response to an invitation to tender'))
            create_if_needed(ProjectStatus, {'pk': 2}, name=_('Initialization'),        order=2, description=_('The project is starting'))
            create_if_needed(ProjectStatus, {'pk': 3}, name=_('Preliminary phase'),     order=3, description=_('The project is in the process of analysis and design'))
            create_if_needed(ProjectStatus, {'pk': 4}, name=_('Achievement'),           order=4, description=_('The project is being implemented'))
            create_if_needed(ProjectStatus, {'pk': 5}, name=_('Tests'),                 order=5, description=_('The project is in the testing process (unit / integration / functional)'))
            create_if_needed(ProjectStatus, {'pk': 6}, name=_('User acceptance tests'), order=6, description=_('The project is in the user acceptance testing process'))
            create_if_needed(ProjectStatus, {'pk': 7}, name=_('Finished'),              order=7, description=_('The project is finished'))

            # ---------------------------
            create_bdl         = BrickDetailviewLocation.objects.create_if_needed
            create_bdl_4_model = BrickDetailviewLocation.objects.create_for_model_brick

            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            create_bdl(brick=bricks.ProjectTasksBrick,      order=2,   zone=TOP,   model=Project)
            create_bdl_4_model(                             order=5,   zone=LEFT,  model=Project)
            create_bdl(brick=bricks.ProjectExtraInfoBrick,  order=30,  zone=LEFT,  model=Project)
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT,  model=Project)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT,  model=Project)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT,  model=Project)
            create_bdl(brick=core_bricks.HistoryBrick,      order=20,  zone=RIGHT, model=Project)

            create_bdl(brick=bricks.TaskResourcesBrick,     order=2,   zone=TOP,   model=ProjectTask)
            create_bdl(brick=bricks.TaskActivitiesBrick,    order=4,   zone=TOP,   model=ProjectTask)
            create_bdl_4_model(                             order=5,   zone=LEFT,  model=ProjectTask)
            create_bdl(brick=bricks.TaskExtraInfoBrick,     order=30,  zone=LEFT,  model=ProjectTask)
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT,  model=ProjectTask)
            create_bdl(brick=bricks.ParentTasksBrick,       order=50,  zone=LEFT,  model=ProjectTask)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT,  model=ProjectTask)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT,  model=ProjectTask)
            create_bdl(brick=core_bricks.HistoryBrick,      order=20,  zone=RIGHT, model=ProjectTask)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants import bricks as a_bricks

                for model in (Project, ProjectTask):
                    create_bdl(brick=a_bricks.TodosBrick,        order=100, zone=RIGHT, model=model)
                    create_bdl(brick=a_bricks.MemosBrick,        order=200, zone=RIGHT, model=model)
                    create_bdl(brick=a_bricks.AlertsBrick,       order=300, zone=RIGHT, model=model)
                    create_bdl(brick=a_bricks.UserMessagesBrick, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                for model in (Project, ProjectTask):
                    create_bdl(brick=LinkedDocsBrick, order=600, zone=RIGHT, model=model)
