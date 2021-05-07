# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.http import Http404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import ButtonMenuItem
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin

from ..forms import button_menu as button_forms
from . import base


class Portal(generic.BricksView):
    template_name = 'creme_config/portals/button-menu.html'


class ButtonMenuWizard(generic.wizard.CremeWizardViewPopup):
    class _ResourceStep(button_forms.ButtonMenuAddForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

        def save(self, commit=False):
            return super().save(commit=commit)

    class _ButtonsStep(button_forms.ButtonMenuEditForm):
        @property
        def step_title(self):
            return gettext('New buttons configuration for «{model}»').format(model=self.ct)

    form_list = [
        _ResourceStep,
        # button_forms.ButtonMenuEditForm,
        _ButtonsStep,
    ]
    title = _('New buttons configuration')
    submit_label = _('Save the configuration')
    permissions = 'creme_core.can_admin'

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)

        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            kwargs['button_menu_items'] = ()
            kwargs['ct_id'] = cleaned_data['ctype'].id

        return kwargs


class ButtonMenuEdition(EntityCTypeRelatedMixin, base.ConfigEdition):
    model = ButtonMenuItem
    form_class = button_forms.ButtonMenuEditForm
    ct_id_0_accepted = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = None

    def get_items(self):
        items = self.items

        if items is None:
            items = ButtonMenuItem.objects.filter(content_type=self.get_ctype()) \
                                          .order_by('order')

            if not items:
                raise Http404('This configuration odes not exist.')

            self.items = items

        return items

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ctype = self.get_ctype()
        kwargs['ct_id'] = None if ctype is None else ctype.id
        kwargs['button_menu_items'] = self.get_items()

        return kwargs

    def get_title(self):
        ctype = self.get_ctype()

        return (
            gettext('Edit configuration for «{model}»').format(model=ctype)
            if ctype else
            gettext('Edit default configuration')
        )


class ButtonMenuDeletion(base.ConfigDeletion):
    ct_id_arg = 'id'

    def perform_deletion(self, request):
        ct_id = get_from_POST_or_404(request.POST, self.ct_id_arg, cast=int)
        ButtonMenuItem.objects.filter(content_type=ct_id).delete()
