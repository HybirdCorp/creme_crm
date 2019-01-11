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

from django.http import Http404, HttpResponse
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from formtools.wizard.views import SessionWizardView

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import ButtonMenuItem
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import BricksView
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin
from creme.creme_core.views.generic.wizard import PopupWizardMixin

from ..forms import button_menu as button_forms

from .base import ConfigEdition


class Portal(BricksView):
    template_name = 'creme_config/button_menu_portal.html'


class ButtonMenuWizard(PopupWizardMixin, SessionWizardView):
    class _ResourceStep(button_forms.ButtonMenuAddForm):
        step_submit_label = pgettext_lazy('creme_config-verb', 'Select')

    class _ConfigStep(button_forms.ButtonMenuEditForm):
        step_prev_label = _('Previous step')
        step_submit_label = _('Save the configuration')

    form_list = (_ResourceStep, _ConfigStep)
    wizard_title = _('New buttons configuration')
    template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
    permission = 'creme_core.can_admin'

    def done(self, form_list, **kwargs):
        # form_list[1].save()
        _resource_form, config_form = form_list
        config_form.save()

        return HttpResponse()

    def get_form_kwargs(self, step):
        kwargs = super().get_form_kwargs(step)

        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            kwargs['button_menu_items'] = ()
            kwargs['ct_id'] = cleaned_data['ctype'].id

        return kwargs


class ButtonMenuEdition(EntityCTypeRelatedMixin, ConfigEdition):
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

        return ugettext('Edit configuration for «{model}»').format(model=ctype) \
               if ctype else \
               ugettext('Edit default configuration')


@login_required
@permission_required('creme_core.can_admin')
def delete(request):
    ct_id = get_from_POST_or_404(request.POST, 'id')
    ButtonMenuItem.objects.filter(content_type=ct_id).delete()

    return HttpResponse()
