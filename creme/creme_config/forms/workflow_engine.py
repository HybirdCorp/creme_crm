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

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.models import WorkflowRule


# class WorkflowRuleCreationForm(CremeModelForm):
#     class Meta:
#         model = WorkflowRule
#         exclude = ()
class RuleCTypeStep(CremeModelForm):
    # TODO?
    # content_type = core_fields.EntityCTypeChoiceField(
    #     label=_('Related resource'),
    #     help_text=_(
    #         'The other custom fields for this type of resource will be chosen '
    #         'by editing the configuration'
    #     ),
    #     widget=DynamicSelect({'autocomplete': True}),
    # )

    class Meta:
        model = WorkflowRule
        fields = ('content_type',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        used_ct_ids = {
            # TODO: .exclude(is_deleted=True)?
            *WorkflowRule.objects.values_list('content_type_id', flat=True),
        }
        ct_field = self.fields['content_type']
        ct_field.ctypes = (ct for ct in ct_field.ctypes if ct.id not in used_ct_ids)


# TODO: factorise
class RuleActionStep(CremeModelForm):
    class Meta:
        model = WorkflowRule
        exclude = ()
