# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

# import warnings

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from formtools.wizard.views import SessionWizardView

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import FieldsConfig
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import edit_model_with_popup  # add_model_with_popup
from creme.creme_core.views.generic.wizard import PopupWizardMixin

from ..forms.fields_config import FieldsConfigAddForm, FieldsConfigEditForm


@login_required
def portal(request):
    return render(request, 'creme_config/fields_config_portal.html',
                  context={'bricks_reload_url': reverse('creme_core__reload_bricks')},
                 )


# @login_required
# @permission_required('creme_core.can_admin')
# def add(request):
#     warnings.warn("creme_config/fields/add/ is now deprecated. "
#                   "Use creme_config/fields/wizard view instead.",
#                   DeprecationWarning
#                  )
#
#     return add_model_with_popup(request, FieldsConfigAddForm,
#                                 title=FieldsConfig.creation_label,
#                                 submit_label=FieldsConfig.save_label,
#                                )


@login_required
@permission_required('creme_core.can_admin')
def edit(request, fconf_id):
    return edit_model_with_popup(request, {'pk': fconf_id}, model=FieldsConfig,
                                 form_class=FieldsConfigEditForm,
                                )


@login_required
@permission_required('creme_core.can_admin')
def delete(request):
    get_object_or_404(FieldsConfig, pk=get_from_POST_or_404(request.POST, 'id')).delete()

    return HttpResponse()


class FieldConfigWizard(PopupWizardMixin, SessionWizardView):
    class _ModelStep(FieldsConfigAddForm):
        step_submit_label = pgettext_lazy('creme_config-verb', u'Select')

        def __init__(self, *args, **kwargs):
            super(FieldConfigWizard._ModelStep, self).__init__(*args, **kwargs)
            if not self.ctypes:
                raise ConflictError(ugettext(u'All configurable types of resource are already configured.'))

    class _ConfigStep(FieldsConfigEditForm):
        step_prev_label = _(u'Previous step')
        step_submit_label = FieldsConfig.save_label

    form_list = (_ModelStep, _ConfigStep)
    wizard_title = FieldsConfig.creation_label
    permission = 'creme_core.can_admin'

    def done(self, form_list, **kwargs):
        configure_step = form_list[1]
        configure_step.save()

        return HttpResponse(content_type='text/javascript')

    def get_form_instance(self, step):
        cleaned_data = self.get_cleaned_data_for_step('0')
        return FieldsConfig(content_type=cleaned_data['ctype'], descriptions=())
