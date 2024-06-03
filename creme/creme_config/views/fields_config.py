################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2024  Hybird
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
from django.utils.translation import gettext as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui import fields_config
from creme.creme_core.models import FieldsConfig
from creme.creme_core.utils import get_from_POST_or_404

from ..bricks import FieldsConfigsBrick
from ..forms import fields_config as fconf_forms
from . import base


class Portal(base.ConfigPortal):
    template_name = 'creme_config/portals/fields-config.html'
    brick_classes = [FieldsConfigsBrick]


class FieldsConfigEdition(base.ConfigModelEdition):
    model = FieldsConfig
    form_class = fconf_forms.FieldsConfigEditionForm
    pk_url_kwarg = 'fconf_id'

    fconfig_registry = fields_config.fields_config_registry

    def check_instance_permissions(self, instance, user):
        if not self.fconfig_registry.is_model_registered(
            instance.content_type.model_class()
        ):
            raise ConflictError(
                'This model is not registered for fields configuration.'
            )


class FieldsConfigDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        get_object_or_404(
            FieldsConfig,
            pk=get_from_POST_or_404(request.POST, self.id_arg),
        ).delete()


class FieldsConfigWizard(base.ConfigModelCreationWizard):
    class _ModelStep(fconf_forms.FieldsConfigCreationForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if not self.ctypes:
                raise ConflictError(
                    _('All configurable types of resource are already configured.')
                )

    class _FieldsStep(fconf_forms.FieldsConfigEditionForm):
        @property
        def step_title(self):
            return _('Create a fields configuration for «{model}»').format(
                model=self.instance.content_type,
            )

    form_list = [
        _ModelStep,
        _FieldsStep,
    ]
    model = FieldsConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cbci = FieldsConfig()

    def get_form_instance(self, step):
        # We fill the instance with the previous step
        # (so recursively all previous should be used)
        self.validate_previous_steps(step)

        return self.cbci
