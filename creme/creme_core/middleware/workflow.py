################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

import warnings

from django.utils.deprecation import MiddlewareMixin

from ..core.workflow import WorkflowEngine


class WorkflowMiddleware(MiddlewareMixin):
    """This Middleware checks the Workflow engine has been run correctly."""
    def process_response(self, request, response):
        events = WorkflowEngine.get_current()._queue.pickup()
        if events:
            warnings.warn(
                f'Some workflow events have not been managed by the view '
                f'"{request.path}": {events}.\n'
                f'Hint: use <creme.creme_core.core.workflow.run_workflow_engine()> '
                f'or the view decorator <creme.creme_core.views.decorators.workflow_engine>',
                RuntimeWarning,
            )

        return response
