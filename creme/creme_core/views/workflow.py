################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from ..gui import bricks
from ..models import Workflow
from . import generic


class WorkflowBarHatBrick(bricks.Brick):
    id = 'workflow_hat_bar'
    dependencies = [Workflow]
    template_name = 'creme_core/bricks/workflow/hat-bar.html'
    # read_only = True TODO?


class WorkflowInfoBrick(bricks.Brick):
    id = 'workflow_info'
    read_only = True
    template_name = 'creme_core/bricks/workflow/info.html'


class WorkflowDetail(generic.CremeModelDetail):
    model = Workflow
    template_name = 'creme_core/detail/workflow.html'
    pk_url_kwarg = 'workflow_id'
    # bricks_reload_url_name = 'creme_core__reload_efilter_bricks' # TODO?
    # permissions # TODO?

    # TODO: declarative way
    def get_bricks(self):
        return {
            'hat': [WorkflowBarHatBrick()],
            # TODO: history of events?
            'main': [WorkflowInfoBrick()],
        }

    # TODO?
    # def get_bricks_reload_url(self):
    #     return reverse(self.bricks_reload_url_name, args=(self.object.id,))
