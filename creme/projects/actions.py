################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2019  Hybird
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

from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from creme import projects
from creme.creme_core.gui import actions


class ProjectCloseAction(actions.UIAction):
    id = actions.UIAction.generate_id('projects', 'close')

    model = projects.get_project_model()
    type = 'projects-close'
    label = _('Close project')
    icon = 'cancel'

    @property
    def url(self):
        return reverse('projects__close_project', args=(self.instance.id,))

    @property
    def is_enabled(self):
        instance = self.instance
        return self.user.has_perm_to_change(instance) and not instance.is_closed
