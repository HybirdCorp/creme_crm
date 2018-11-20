# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CustomField
from creme.creme_core.utils import get_from_POST_or_404  # get_ct_or_404
from creme.creme_core.views.generic import BricksView
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin

from ..forms import custom_fields as cf_forms

from . import base
# from .portal import _config_portal


# @login_required
# @permission_required('creme_core.can_admin')
# def add_ct(request):
#     return generic.add_model_with_popup(
#               request, cf_forms.CustomFieldsCTAddForm,
#               _('New custom field configuration'),
#               submit_label=_('Save the configuration'),
#     )
class FirstCTypeCustomFieldCreation(base.ConfigModelCreation):
    model = CustomField
    form_class = cf_forms.CustomFieldsCTAddForm
    title = _('New custom field configuration')


# @login_required
# @permission_required('creme_core.can_admin')
# def add(request, ct_id):
#     ct = get_ct_or_404(ct_id)
#
#     return generic.add_model_with_popup(request, cf_forms.CustomFieldsAddForm,
#                             ugettext('New custom field for «{model}»').format(model=ct),
#                             initial={'ct': ct},
#                            )
class CustomFieldCreation(EntityCTypeRelatedMixin,
                          base.ConfigModelCreation,
                         ):
    model = CustomField
    form_class = cf_forms.CustomFieldsAddForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ctype'] = self.get_ctype()

        return kwargs

    def get_title(self):
        return ugettext('New custom field for «{model}»').format(
            model=self.get_ctype(),
        )


# @login_required
# def portal(request):
#     return _config_portal(request, 'creme_config/custom_fields_portal.html')
class Portal(BricksView):
    template_name = 'creme_config/custom_fields_portal.html'


# @login_required
# @permission_required('creme_core.can_admin')
# def edit(request, field_id):
#     return generic.edit_model_with_popup(request, {'pk': field_id},
#                                          CustomField, cf_forms.CustomFieldsEditForm,
#                                         )
class CustomFieldEdition(base.ConfigModelEdition):
    model = CustomField
    form_class = cf_forms.CustomFieldsEditForm
    pk_url_kwarg = 'field_id'


@login_required
@permission_required('creme_core.can_admin')
def delete_ct(request):
    for field in CustomField.objects.filter(content_type=get_from_POST_or_404(request.POST, 'id')):
        field.delete()

    return HttpResponse()


@login_required
@permission_required('creme_core.can_admin')
def delete(request):
    field = CustomField.objects.get(pk=get_from_POST_or_404(request.POST, 'id'))
    field.delete()

    return HttpResponse()
