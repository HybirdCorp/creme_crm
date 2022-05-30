# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from creme.creme_core.forms import LAYOUT_DUAL_FIRST, LAYOUT_DUAL_SECOND
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    CustomFormConfigItem,
    HeaderFilter,
    MenuConfigItem,
    RelationType,
    SearchConfigItem,
)
from creme.creme_core.utils import create_if_needed
from creme.persons import get_contact_model

from . import (
    bricks,
    constants,
    custom_forms,
    get_project_model,
    get_task_model,
)
from .forms.project import ProjectLeadersSubCell
from .forms.task import ParentTasksSubCell
from .menu import ProjectsEntry
from .models import ProjectStatus, TaskStatus

logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'activities']

    def populate(self):
        already_populated = RelationType.objects.filter(
            pk=constants.REL_SUB_PROJECT_MANAGER,
        ).exists()
        Contact = get_contact_model()
        Activity = get_activity_model()

        Project     = get_project_model()
        ProjectTask = get_task_model()

        create_rtype = RelationType.objects.smart_update_or_create
        create_rtype(
            (
                constants.REL_SUB_PROJECT_MANAGER,
                _('is one of the leaders of this project'),
                [Contact],
            ), (
                constants.REL_OBJ_PROJECT_MANAGER,
                _('has as leader'),
                [Project],
            ),
        )
        create_rtype(
            (
                constants.REL_SUB_LINKED_2_PTASK,
                _('is related to the task of project'),
                [Activity],
            ), (
                constants.REL_OBJ_LINKED_2_PTASK,
                _('includes the activity'),
                [ProjectTask],
            ),
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
            create_if_needed(
                TaskStatus, {'pk': pk}, name=str(statusdesc.name), order=pk,
                description=str(statusdesc.verbose_name), is_custom=False,
            )

        # ---------------------------
        create_hf = HeaderFilter.objects.create_if_needed
        create_hf(
            pk=constants.DEFAULT_HFILTER_PROJECT,
            model=Project,
            name=_('Project view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'start_date'}),
                (EntityCellRegularField, {'name': 'end_date'}),
                (EntityCellRegularField, {'name': 'status'}),
                (EntityCellRegularField, {'name': 'description'}),
            ],
        )

        # Used in form
        create_hf(
            pk='projects-hf_task', name=_('Task view'), model=ProjectTask,
            cells_desc=[
                (EntityCellRegularField, {'name': 'title'}),
                (EntityCellRegularField, {'name': 'description'}),
            ],
        )

        # ---------------------------
        common_groups_desc = [
            {
                'name': _('Description'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            }, {
                'name': _('Custom fields'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                    ),
                ],
            },
        ]
        only_creation_groups_desc = [
            {
                'name': _('Properties'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                    ),
                ],
            }, {
                'name': _('Relationships'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.RELATIONS},
                    ),
                ],
            },
        ]

        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.PROJECT_CREATION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                        (EntityCellRegularField, {'name': 'status'}),
                        ProjectLeadersSubCell(model=Project).into_cell(),
                        (EntityCellRegularField, {'name': 'start_date'}),
                        (EntityCellRegularField, {'name': 'end_date'}),
                        (EntityCellRegularField, {'name': 'currency'}),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
                *only_creation_groups_desc,
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.PROJECT_EDITION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                        (EntityCellRegularField, {'name': 'status'}),
                        (EntityCellRegularField, {'name': 'start_date'}),
                        (EntityCellRegularField, {'name': 'end_date'}),
                        (EntityCellRegularField, {'name': 'currency'}),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
            ],
        )

        task_rfields_cells = [
            (EntityCellRegularField, {'name': 'user'}),
            (EntityCellRegularField, {'name': 'title'}),
            (EntityCellRegularField, {'name': 'start'}),
            (EntityCellRegularField, {'name': 'end'}),
            (EntityCellRegularField, {'name': 'duration'}),
            (EntityCellRegularField, {'name': 'tstatus'}),
        ]
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.TASK_CREATION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        *task_rfields_cells,
                        ParentTasksSubCell(model=ProjectTask).into_cell(),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
                *only_creation_groups_desc,
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.TASK_EDITION_CFORM,
            groups_desc=[
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        *task_rfields_cells,
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                *common_groups_desc,
            ],
        )

        # ---------------------------
        create_searchconf = SearchConfigItem.objects.create_if_needed
        create_searchconf(
            Project,
            ['name', 'description', 'status__name'],
        )
        create_searchconf(
            ProjectTask,
            ['linked_project__name', 'duration', 'tstatus__name'],
        )

        # ---------------------------
        # TODO: move to "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='projects-').exists():
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Tools')},
                defaults={'order': 100},
            )[0]

            MenuConfigItem.objects.create(
                entry_id=ProjectsEntry.id, parent=container, order=50,
            )

        # ---------------------------
        if not already_populated:
            for pk, (name, description) in enumerate([
                (
                    _('Invitation to tender'),
                    _('Response to an invitation to tender'),
                ), (
                    _('Initialization'),
                    _('The project is starting'),
                ), (
                    _('Preliminary phase'),
                    _('The project is in the process of analysis and design'),
                ), (
                    _('Achievement'),
                    _('The project is being implemented'),
                ), (
                    _('Tests'),
                    _('The project is in the testing process (unit / integration / functional)'),
                ), (
                    _('User acceptance tests'),
                    _('The project is in the user acceptance testing process'),
                ), (
                    _('Finished'),
                    _('The project is finished')
                ),
            ], start=1):
                create_if_needed(
                    ProjectStatus, {'pk': pk},
                    name=name, order=pk, description=description,
                )

            # ---------------------------
            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Project, 'zone': LEFT},
                data=[
                    {'brick': bricks.ProjectTasksBrick, 'order': 2, 'zone': TOP},

                    {'order': 5},
                    {'brick': bricks.ProjectExtraInfoBrick,  'order':  30},
                    {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': ProjectTask, 'zone': LEFT},
                data=[
                    {'brick': bricks.TaskResourcesBrick,  'order': 2, 'zone': TOP},
                    {'brick': bricks.TaskActivitiesBrick, 'order': 4, 'zone': TOP},

                    {'order': 5},
                    {'brick': bricks.TaskExtraInfoBrick,     'order':  30},
                    {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                    {'brick': bricks.ParentTasksBrick,       'order':  50},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail views'
                )

                from creme.assistants import bricks as a_bricks

                for model in (Project, ProjectTask):
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
                # logger.info('Documents app is installed
                # => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'brick': LinkedDocsBrick, 'order': 600, 'zone': RIGHT},
                    data=[{'model': model} for model in (Project, ProjectTask)],
                )
