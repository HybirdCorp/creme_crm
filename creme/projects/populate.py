# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import info

from django.utils.translation import ugettext as _
from django.conf import settings

from creme_core.models import RelationType, SearchConfigItem, HeaderFilterItem, HeaderFilter, BlockDetailviewLocation
from creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Contact

from projects.models import ProjectStatus, TaskStatus, Project, ProjectTask, Resource
from projects.blocks import *
from projects.constants import REL_OBJ_PROJECT_MANAGER, REL_SUB_PROJECT_MANAGER, TASK_STATUS


class Populator(BasePopulator):
    dependencies = ['creme.creme_core', 'creme.persons', 'creme.activities']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_PROJECT_MANAGER, _(u'is one of the leaders of this project'), [Contact]),
                            (REL_OBJ_PROJECT_MANAGER, _(u'has as leader'),                         [Project]))

        create(ProjectStatus, 1, name=_(u"Invitation to tender"),  description=_(u"Response to an invitation to tender"))
        create(ProjectStatus, 2, name=_(u"Initialization"),        description=_(u"The project is starting"))
        create(ProjectStatus, 3, name=_(u"Preliminary phase"),     description=_(u"The project is in the process of analysis and design"))
        create(ProjectStatus, 4, name=_(u"Achievement"),           description=_(u"The project is being implemented"))
        create(ProjectStatus, 5, name=_(u"Tests"),                 description=_(u"The project is in the testing process (unit / integration / functional)"))
        create(ProjectStatus, 6, name=_(u"User acceptance tests"), description=_(u"The project is in the user acceptance testing process"))
        create(ProjectStatus, 7, name=_(u"Finished"),              description=_(u"The project is finished"))

        for pk, statusdesc in TASK_STATUS.iteritems():
            create(TaskStatus, pk, name=unicode(statusdesc.name), description=unicode(statusdesc.verbose_name), is_custom=False)

        hf = HeaderFilter.create(pk='projects-hf_project', name=_(u'Project view'), model=Project)
        hf.set_items([HeaderFilterItem.build_4_field(model=Project, name='name'),
                      HeaderFilterItem.build_4_field(model=Project, name='description'),
                     ])

        #used in form
        hf = HeaderFilter.create(pk='projects-hf_task', name=_(u'Task view'), model=ProjectTask)
        hf.set_items([HeaderFilterItem.build_4_field(model=ProjectTask, name='title'),
                      HeaderFilterItem.build_4_field(model=ProjectTask, name='description'),
                     ])

        #used in form
        hf = HeaderFilter.create(pk='projects-hf_resource', name=_(u'Resource view'), model=Resource)
        hf.set_items([HeaderFilterItem.build_4_field(model=Resource, name='linked_contact'),
                      HeaderFilterItem.build_4_field(model=Resource, name='hourly_cost'),
                     ])

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
            info('Assistants app is installed => we use the assistants blocks on detail views')

            from assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            for model in (Project, ProjectTask):
                BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=model)

        SearchConfigItem.create(Project,     ['name', 'description', 'status__name'])
        SearchConfigItem.create(Resource,    ['linked_contact__first_name', 'linked_contact__last_name', 'hourly_cost'])
        SearchConfigItem.create(ProjectTask, ['project__name', 'duration', 'tstatus__name'])
