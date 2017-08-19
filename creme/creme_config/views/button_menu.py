# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

import warnings

from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse
from django.utils.translation import ugettext as _

from formtools.wizard.views import SessionWizardView

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import ButtonMenuItem
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import add_model_with_popup, inner_popup
from creme.creme_core.views.generic.wizard import PopupWizardMixin

from ..forms.button_menu import ButtonMenuAddForm, ButtonMenuEditForm
from .portal import _config_portal


@login_required
def portal(request):
    return _config_portal(request, 'creme_config/button_menu_portal.html')


@login_required
@permission_required('creme_core.can_admin')
def add(request):
    warnings.warn('creme_config/button_menu/add is now deprecated. Use creme_config/button_menu/wizard view instead.',
                  DeprecationWarning
                 )

    return add_model_with_popup(request, ButtonMenuAddForm,
                                _(u'New buttons configuration'),
                                submit_label=_(u'Save the configuration'),
                               )


class ButtonMenuWizard(PopupWizardMixin, SessionWizardView):
    class _ResourceStep(ButtonMenuAddForm):
        step_submit_label = _(u'Select')

    class _ConfigStep(ButtonMenuEditForm):
        step_prev_label = _(u'Previous step')
        step_submit_label = _(u'Save the configuration')

    form_list = (_ResourceStep, _ConfigStep)
    wizard_title = _(u'New buttons configuration')
    template_name = 'creme_core/generics/blockform/add_wizard_popup.html'
    permission = 'creme_core.can_admin'

    def done(self, form_list, **kwargs):
        form_list[1].save()

        return HttpResponse(content_type='text/javascript')

    def get_form_kwargs(self, step):
        kwargs = super(ButtonMenuWizard, self).get_form_kwargs(step)

        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            kwargs['button_menu_items'] = ()
            kwargs['ct_id'] = cleaned_data['ctype'].id

        return kwargs


@login_required
@permission_required('creme_core.can_admin')
def edit(request, ct_id):
    ct_id = int(ct_id) or None
    bmi = ButtonMenuItem.objects.filter(content_type=ct_id).order_by('order')

    if not bmi:
        raise Http404  # Meh

    if request.method == 'POST':
        buttons_form = ButtonMenuEditForm(bmi, ct_id, user=request.user, data=request.POST)

        if buttons_form.is_valid():
            buttons_form.save()
    else:
        buttons_form = ButtonMenuEditForm(bmi, ct_id, user=request.user)

    title = _(u'Edit configuration for «%s»') % ContentType.objects.get_for_id(ct_id) \
            if ct_id else \
            _(u'Edit default configuration')

    return inner_popup(request,
                       'creme_core/generics/blockform/edit_popup.html',
                       {'form':  buttons_form,
                        'title': title,
                        'submit_label': _(u'Save the modifications'),
                       },
                       is_valid=buttons_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


@login_required
@permission_required('creme_core.can_admin')
def delete(request):
    ct_id = get_from_POST_or_404(request.POST, 'id')
    ButtonMenuItem.objects.filter(content_type=ct_id).delete()

    return HttpResponse()
