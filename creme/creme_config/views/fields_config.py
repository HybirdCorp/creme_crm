# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2019  Hybird
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

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _, pgettext_lazy

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import FieldsConfig
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import BricksView

from ..forms import fields_config as fconf_forms

from . import base


class Portal(BricksView):
    template_name = 'creme_config/fields_config_portal.html'


class FieldsConfigEdition(base.ConfigModelEdition):
    model = FieldsConfig
    form_class = fconf_forms.FieldsConfigEditForm
    pk_url_kwarg = 'fconf_id'


class FieldsConfigDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        get_object_or_404(
            FieldsConfig,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        ).delete()


class FieldsConfigWizard(base.ConfigModelCreationWizard):
    class _ModelStep(fconf_forms.FieldsConfigAddForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if not self.ctypes:
                raise ConflictError(_('All configurable types of resource are already configured.'))

    form_list = (
        _ModelStep,
        fconf_forms.FieldsConfigEditForm,
    )
    model = FieldsConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cbci = FieldsConfig()

    def get_form_instance(self, step):
        # We fill the instance with the previous step (so recursively all previous should be used)
        self.validate_previous_steps(step)

        return self.cbci
