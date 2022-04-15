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

from ..core.workflow import WorkflowEngine


class WorkflowMiddleware(MiddlewareMixin):
    """This Middleware runs the Workflow engine.

    The main reason this is done here (& not directly in a signal handler, when
    an entity is created/edited/...) is to get "complete" entity. When you
    save() a CremeEntity instance, its ManyToManyFields (or CustomFields/
    Relations/CremeProperties/...) are not up-to-date yet with the values the
    user just has submitted. So conditions on ManyToManyFields won't check the
    correct state of the Entity. So by running the Workflow after the view/forms
    have finished their job we can check the final state of the entities as
    expected.

    Working with an event queue which content is "captured" allows us to avoid
    cycle (when an Action generates some Events that also trigger a workflow,
    etc...). In a futur version, we can imagine to treat a limited number of
    "generations" (instead of just one currently).
    """
    def process_response(self, request, response):
        WorkflowEngine().run(user=request.user)

        return response
