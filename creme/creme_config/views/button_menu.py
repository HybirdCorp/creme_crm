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

# import warnings

# from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from formtools.wizard.views import SessionWizardView

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import ButtonMenuItem
from creme.creme_core.utils import get_from_POST_or_404
# from creme.creme_core.views.generic import inner_popup
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin
from creme.creme_core.views.generic.wizard import PopupWizardMixin

from ..forms import button_menu as button_forms

from .base import BaseConfigEdition
from .portal import _config_portal


@login_required
def portal(request):
    return _config_portal(request, 'creme_config/button_menu_portal.html')


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
        # kwargs = super(ButtonMenuWizard, self).get_form_kwargs(step)
        kwargs = super().get_form_kwargs(step)

        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            kwargs['button_menu_items'] = ()
            kwargs['ct_id'] = cleaned_data['ctype'].id

        return kwargs


# @login_required
# @permission_required('creme_core.can_admin')
# def edit(request, ct_id):
#     ct_id = int(ct_id) or None
#     bmi = ButtonMenuItem.objects.filter(content_type=ct_id).order_by('order')
#
#     if not bmi:
#         raise Http404  # Meh
#
#     if request.method == 'POST':
#         buttons_form = button_forms.ButtonMenuEditForm(bmi, ct_id, user=request.user, data=request.POST)
#
#         if buttons_form.is_valid():
#             buttons_form.save()
#     else:
#         buttons_form = button_forms.ButtonMenuEditForm(bmi, ct_id, user=request.user)
#
#     # todo: lazy interpolation ??
#     title = ugettext('Edit configuration for «{model}»').format(model=ContentType.objects.get_for_id(ct_id)) \
#             if ct_id else \
#             _('Edit default configuration')
#
#     return inner_popup(request,
#                        'creme_core/generics/blockform/edit_popup.html',
#                        {'form':  buttons_form,
#                         'title': title,
#                         'submit_label': _('Save the modifications'),
#                        },
#                        is_valid=buttons_form.is_valid(),
#                        reload=False,
#                        delegate_reload=True,
#                       )
class ButtonMenuEdition(EntityCTypeRelatedMixin, BaseConfigEdition):
    model = ButtonMenuItem
    # pk_url_kwarg = ''
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

    def get_object(self, *args, **kwargs):
        return None

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
