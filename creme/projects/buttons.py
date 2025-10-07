################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from creme.creme_core.gui.button_menu import Button

from . import get_project_model

Project = get_project_model()


class CloseProjectButton(Button):
    id = Button.generate_id('projects', 'close')
    verbose_name = 'Close the project'
    # description = _(
    #     'This button ....\n'
    #     'App: Projects'
    # )
    dependencies = (Project,)
    template_name = 'projects/buttons/close-project.html'
    permissions = 'projects'

    def get_ctypes(self):
        return (Project,)

    # def ok_4_display(self, entity):
    def is_displayed(self, *, entity, request):
        return not entity.is_closed
