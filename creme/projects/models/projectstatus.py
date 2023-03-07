################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

import creme.creme_core.models.fields as core_fields
from creme.creme_core.models import MinionModel


class ProjectStatus(MinionModel):
    name = models.CharField(_('Name'), max_length=100)
    color_code = core_fields.ColorField(_('Color'), blank=True)
    description = models.TextField(_('Description'))
    order = core_fields.BasicAutoField()  # Used by creme_config

    creation_label = pgettext_lazy('projects-project_status', 'Create a status')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'projects'
        verbose_name = pgettext_lazy('projects-singular', 'Status of project')
        verbose_name_plural = pgettext_lazy('projects-plural', 'Status of project')
        ordering = ('order',)
