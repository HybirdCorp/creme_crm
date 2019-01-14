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

# from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.functional import cached_property
# from django.utils.translation import ugettext as _

# from ..auth.decorators import login_required
from ..gui.quick_forms import quickforms_registry
# from ..utils import get_ct_or_404

from . import generic
from .generic.base import EntityCTypeRelatedMixin
from .utils import json_update_from_widget_response


# @login_required
# def add(request, ct_id, count):
#     warnings.warn('creme_core.views.quick_forms.add() is deprecated.', DeprecationWarning)
#
#     # NB: it seems there is a problem with formsets : if the 'user' field is empty
#     #     it does not raise a Validation exception, but it causes a SQL integrity
#     #     error ; we are saved by the 'empty_label=None' of user field, but it is
#     #     not really perfect...
#
#     from django.forms.formsets import formset_factory
#
#     if count == '0':
#         raise Http404('Count must be between 1 & 9')
#
#     model = get_ct_or_404(ct_id).model_class()
#     model_name = model._meta.verbose_name
#     user = request.user
#
#     if not user.has_perm_to_create(model):
#         # TODO: manage/display error on js side (for now it just does nothing)
#         raise PermissionDenied('You are not allowed to create entity with type "{}"'.format(model_name))
#
#     base_form_class = quickforms_registry.get_form(model)
#
#     if base_form_class is None:
#         raise Http404('No form registered for model: {}'.format(model))
#
#     # We had the mandatory 'user' argument
#     class _QuickForm(base_form_class):
#         def __init__(self, *args, **kwargs):
#             super().__init__(user=user, *args, **kwargs)
#             # HACK : empty_permitted attribute allows formset to remove fields data that hasn't change from initial.
#             # This behaviour force user_id value to null when form is empty and causes an SQL integrity error.
#             # In django 1.3 empty_permitted cannot be set correctly so force it.
#             self.empty_permitted = False
#
#     qformset_class = formset_factory(_QuickForm, extra=int(count))
#
#     if request.method == 'POST':
#         qformset = qformset_class(data=request.POST, files=request.FILES or None)
#
#         if qformset.is_valid():
#             for form in qformset:
#                 form.save()
#     else:
#         qformset = qformset_class()
#
#     return generic.inner_popup(
#         request, 'creme_core/generics/blockformset/add_popup.html',
#         {'formset': qformset,
#          'title':   _('Quick creation of «{model}»').format(model=model_name),
#         },
#         is_valid=qformset.is_valid(),
#         reload=False,
#         delegate_reload=True,
#     )


# TODO: manage/display error (like PermissionDenied) on JS side (for now it just does nothing)
class QuickCreation(EntityCTypeRelatedMixin, generic.EntityCreationPopup):
    # model = ...
    # form_class = ...
    template_name = 'creme_core/generics/form/add-popup.html'

    quickforms_registry = quickforms_registry

    def get_form_class(self):
        model = self.model
        form_class = self.quickforms_registry.get_form(model)

        if form_class is None:
            raise Http404('No form registered for model: {}'.format(model))

        return form_class

    def form_valid(self, form):
        super().form_valid(form=form)
        return json_update_from_widget_response(form.instance)

    @cached_property
    def model(self):
        return self.get_ctype().model_class()
