# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CustomField
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import BricksView
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin

from ..forms import custom_fields as cf_forms

from . import base


class FirstCTypeCustomFieldCreation(base.ConfigModelCreation):
    model = CustomField
    form_class = cf_forms.CustomFieldsCTAddForm
    title = _('New custom field configuration')


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
        return gettext('New custom field for «{model}»').format(
            model=self.get_ctype(),
        )


class Portal(BricksView):
    template_name = 'creme_config/custom_fields_portal.html'


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
