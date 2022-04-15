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

# from django.shortcuts import get_object_or_404
# from django.utils.translation import gettext as _
# from creme.creme_core.core.exceptions import ConflictError
# from creme.creme_core.utils import get_from_POST_or_404
# from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin
# from ..forms import search as search_forms
from creme.creme_core.models import WorkflowRule
from creme.creme_core.views.generic import BricksView

# from ..forms.workflow_engine import WorkflowRuleCreationForm
from ..forms import workflow_engine as workflow_forms
from . import base


class Portal(BricksView):
    template_name = 'creme_config/portals/workflow-engine.html'


# class WorkflowRuleCreation(base.ConfigModelCreation):
#     model = WorkflowRule
#     form_class = WorkflowRuleCreationForm

# TODO: config view for that (see user_role
class FirstCTypeWorkflowRuleCreationWizard(base.ConfigModelCreationWizard):
    form_list = [
        workflow_forms.RuleCTypeStep,
        workflow_forms.RuleActionStep,
    ]
    model = WorkflowRule
