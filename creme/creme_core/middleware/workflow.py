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

from django.utils.deprecation import MiddlewareMixin

from ..core.workflow import WorkflowEventQueue
from ..models import Workflow


class WorkflowMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        """
        TODO
        """
        # TODO: should we merge some events (ex: several editions into one)?
        # TODO: manage errors (log them with a specific model)
        #       + transactions
        events = WorkflowEventQueue.get_current().pickup()
        if events:
            workflows = Workflow.objects.filter(enabled=True)

            for event in events:
                for workflow in workflows:
                    ctxt = workflow.trigger.activate(event)
                    if ctxt:  # TODO: and workflow.accept(ctxt)
                        for action in workflow.actions:
                            action.execute(ctxt)

        return response
