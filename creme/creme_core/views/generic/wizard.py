# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2018  Hybird
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

from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator

from creme.creme_core.auth.decorators import login_required


class PopupWizardMixin:
    """
        Convenient mixin class for wizard popups.
        Handle permissions and build common template context.
    """
    template_name = 'creme_core/generics/blockform/wizard_popup.html'
    wizard_title = ''
    permission = None

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        perm = self.permission
        if perm and not self.request.user.has_perm(perm):
            raise PermissionDenied('You are not allowed to view this form')

        return super(PopupWizardMixin, self).dispatch(*args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super(PopupWizardMixin, self).get_context_data(form=form, **kwargs)
        context['title'] = getattr(form, 'step_title', self.wizard_title)
        context['prev_label'] = getattr(form, 'step_prev_label', '')
        context['first_label'] = getattr(form, 'step_first_label', '')
        context['submit_label'] = getattr(form, 'step_submit_label', '')

        return context

    def get_form_kwargs(self, step):
        return {'user': self.request.user}
