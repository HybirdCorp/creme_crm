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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.registry import creme_registry
from creme.creme_core.gui import creme_menu, block_registry, icon_registry

from creme.projects.models import Project, ProjectTask
from creme.projects.blocks import block_list


creme_registry.register_app('projects', _(u'Projects'), '/projects')
creme_registry.register_entity_models(Project, ProjectTask) #TODO: need to register ProjectTask ??

reg_item = creme_menu.register_app('projects', '/projects/').register_item
reg_item('/projects/',            _('Portal of projects'), 'projects')
reg_item('/projects/projects',    _('All projects'),       'projects')
reg_item('/projects/project/add', Project.creation_label,  'projects.add_project')

block_registry.register(*block_list)

reg_icon = icon_registry.register
reg_icon(Project,     'images/project_%(size)s.png')
reg_icon(ProjectTask, 'images/task_%(size)s.png')
