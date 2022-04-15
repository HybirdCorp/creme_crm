# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022  Hybird
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

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from .base import CremeModel
from .fields import EntityCTypeForeignKey


class WorkflowRule(CremeModel):
    content_type = EntityCTypeForeignKey(verbose_name=_('Related resource'))

    creation_label = pgettext_lazy('creme_config-workflow_engine', 'Create a rule')
    save_label = pgettext_lazy('creme_config-workflow_engine', 'Save the rule')

    # def __str__(self):
    #     return str(self.value)

    class Meta:
        app_label = 'creme_core'
        verbose_name = pgettext_lazy('creme_config-workflow_engine', 'Rule')
        verbose_name_plural = pgettext_lazy('creme_config-workflow_engine', 'Rules')
        # ordering = ('value',)
