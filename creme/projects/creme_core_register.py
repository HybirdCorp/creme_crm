# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu
from creme_core.gui.block import block_registry

from projects.models import Project, ProjectTask, Resource
from projects.blocks import *


creme_registry.register_app('projects', _(u'Projects'), '/projects')
creme_registry.register_entity_models(Project, Resource, ProjectTask)

creme_menu.register_app('projects', '/projects/', 'Projets')
reg_menu = creme_menu.register_item
reg_menu('projects', '/projects/',            _('Portal'),        'projects')
reg_menu('projects', '/projects/projects',    _('All projects'),  'projects')
reg_menu('projects', '/projects/project/add', _('Add a project'), 'projects.add_project')

block_registry.register(project_extra_info, task_extra_info, tasks_block, resources_block, working_periods_block)
