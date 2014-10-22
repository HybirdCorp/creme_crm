# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.conf import settings
from django.utils.translation import ugettext as _

from creme.creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import RelationType, SearchConfigItem, HeaderFilter, BlockDetailviewLocation
from creme.creme_core.utils import create_if_needed

from creme.persons.models import Contact

from .blocks import *
from .constants import REL_OBJ_PROJECT_MANAGER, REL_SUB_PROJECT_MANAGER, TASK_STATUS
from .models import ProjectStatus, TaskStatus


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'activities']

    def populate(self):
        RelationType.create((REL_SUB_PROJECT_MANAGER, _(u'is one of the leaders of this project'), [Contact]),
                            (REL_OBJ_PROJECT_MANAGER, _(u'has as leader'),                         [Project]))

        create_if_needed(ProjectStatus, {'pk': 1}, name=_(u"Invitation to tender"),  order=1, description=_(u"Response to an invitation to tender"))
        create_if_needed(ProjectStatus, {'pk': 2}, name=_(u"Initialization"),        order=2, description=_(u"The project is starting"))
        create_if_needed(ProjectStatus, {'pk': 3}, name=_(u"Preliminary phase"),     order=3, description=_(u"The project is in the process of analysis and design"))
        create_if_needed(ProjectStatus, {'pk': 4}, name=_(u"Achievement"),           order=4, description=_(u"The project is being implemented"))
        create_if_needed(ProjectStatus, {'pk': 5}, name=_(u"Tests"),                 order=5, description=_(u"The project is in the testing process (unit / integration / functional)"))
        create_if_needed(ProjectStatus, {'pk': 6}, name=_(u"User acceptance tests"), order=6, description=_(u"The project is in the user acceptance testing process"))
        create_if_needed(ProjectStatus, {'pk': 7}, name=_(u"Finished"),              order=7, description=_(u"The project is finished"))

        for pk, statusdesc in TASK_STATUS.iteritems():
            create_if_needed(TaskStatus, {'pk': pk}, name=unicode(statusdesc.name), order=pk,
                             description=unicode(statusdesc.verbose_name), is_custom=False,
                            )

        create_hf = HeaderFilter.create
        create_hf(pk='projects-hf_project', name=_(u'Project view'), model=Project,
                  cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                              (EntityCellRegularField, {'name': 'description'}),
                             ],
                 )

        #used in form
        create_hf(pk='projects-hf_task', name=_(u'Task view'), model=ProjectTask,
                  cells_desc=[(EntityCellRegularField, {'name': 'title'}),
                              (EntityCellRegularField, {'name': 'description'}),
                             ],
                 )

        #used in form
        create_hf(pk='projects-hf_resource', name=_(u'Resource view'), model=Resource,
                  cells_desc=[(EntityCellRegularField, {'name': 'linked_contact'}),
                              (EntityCellRegularField, {'name': 'hourly_cost'}),
                             ],
                 )

        BlockDetailviewLocation.create(block_id=project_tasks_block.id_, order=2,   zone=BlockDetailviewLocation.TOP,   model=Project)
        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=Project)
        BlockDetailviewLocation.create(block_id=project_extra_info.id_,  order=30,  zone=BlockDetailviewLocation.LEFT,  model=Project)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,  order=40,  zone=BlockDetailviewLocation.LEFT,  model=Project)
        BlockDetailviewLocation.create(block_id=properties_block.id_,    order=450, zone=BlockDetailviewLocation.LEFT,  model=Project)
        BlockDetailviewLocation.create(block_id=relations_block.id_,     order=500, zone=BlockDetailviewLocation.LEFT,  model=Project)
        BlockDetailviewLocation.create(block_id=history_block.id_,       order=20,  zone=BlockDetailviewLocation.RIGHT, model=Project)

        BlockDetailviewLocation.create(block_id=task_resources_block.id_,      order=2,   zone=BlockDetailviewLocation.TOP,   model=ProjectTask)
        BlockDetailviewLocation.create(block_id=task_workingperiods_block.id_, order=4,   zone=BlockDetailviewLocation.TOP,   model=ProjectTask)
        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=ProjectTask)
        BlockDetailviewLocation.create(block_id=task_extra_info.id_,           order=30,  zone=BlockDetailviewLocation.LEFT,  model=ProjectTask)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,        order=40,  zone=BlockDetailviewLocation.LEFT,  model=ProjectTask)
        BlockDetailviewLocation.create(block_id=parent_tasks_block.id_,        order=50,  zone=BlockDetailviewLocation.LEFT,  model=ProjectTask)
        BlockDetailviewLocation.create(block_id=properties_block.id_,          order=450, zone=BlockDetailviewLocation.LEFT,  model=ProjectTask)
        BlockDetailviewLocation.create(block_id=relations_block.id_,           order=500, zone=BlockDetailviewLocation.LEFT,  model=ProjectTask)
        BlockDetailviewLocation.create(block_id=history_block.id_,             order=20,  zone=BlockDetailviewLocation.RIGHT, model=ProjectTask)

        if 'creme.assistants' in settings.INSTALLED_APPS:
            logger.info('Assistants app is installed => we use the assistants blocks on detail views')

            from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            for model in (Project, ProjectTask):
                BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=model)

        SearchConfigItem.create_if_needed(Project,     ['name', 'description', 'status__name'])
        SearchConfigItem.create_if_needed(Resource,    ['linked_contact__first_name', 'linked_contact__last_name', 'hourly_cost'])
        SearchConfigItem.create_if_needed(ProjectTask, ['project__name', 'duration', 'tstatus__name'])
