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

import warnings

from django.core.exceptions import PermissionDenied
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _, ugettext
from django.views.generic import UpdateView

from creme.creme_core import forms, models
from creme.creme_core.auth.decorators import login_required

from . import base
from .popup import inner_popup


def edit_entity(request, object_id, model, edit_form,
                template='creme_core/generics/blockform/edit.html',
               ):
    warnings.warn('creme_core.views.generic.edit.edit_entity() is deprecated ; '
                  'use the class-based views CremeModelEdition/EntityEdition instead.',
                  DeprecationWarning
                 )

    from django.shortcuts import render, redirect

    from ..utils import build_cancel_path

    entity = get_object_or_404(model, pk=object_id)
    user = request.user

    user.has_perm_to_change_or_die(entity)

    if request.method == 'POST':
        POST = request.POST
        form = edit_form(user=user, data=POST, files=request.FILES or None, instance=entity)

        if form.is_valid():
            form.save()

            return redirect(entity)

        cancel_url = POST.get('cancel_url')
    else:  # GET
        form = edit_form(user=user, instance=entity)
        cancel_url = build_cancel_path(request)

    return render(request, template,
                  {'form': form,
                   'object': entity,
                   'submit_label': _('Save the modifications'),
                   'cancel_url': cancel_url,
                  })


def edit_related_to_entity(request, pk, model, form_class, title_format,
                           submit_label=_('Save the modifications'),
                           template='creme_core/generics/blockform/edit_popup.html',
                          ):
    """Edit a model related to a CremeEntity.
    @param model: A django model class which implements the method get_related_entity().
    @param form_class: Form which __init__'s method MUST HAVE an argument called
                      'entity' (the related CremeEntity).
    @param model: title_format A format unicode with an arg (for the related entity).
    """
    auxiliary = get_object_or_404(model, pk=pk)
    entity = auxiliary.get_related_entity()
    user = request.user

    user.has_perm_to_change_or_die(entity)

    if request.method == 'POST':
        edit_form = form_class(entity=entity, user=user, data=request.POST,
                               files=request.FILES or None, instance=auxiliary,
                              )

        if edit_form.is_valid():
            edit_form.save()
    else:  # return page on GET request
        edit_form = form_class(entity=entity, user=user, instance=auxiliary)

    return inner_popup(request, template,
                       {'form':  edit_form,
                        'title': title_format % entity,
                        'submit_label': submit_label,
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


def edit_model_with_popup(request, query_dict, model, form_class,
                          title_format=None, can_change=None,
                          template='creme_core/generics/blockform/edit_popup.html',
                          submit_label=_('Save the modifications'),
                         ):
    """Get & edit an instance in a inner popup.
    @param query_dict A dictionary which represents the query to retrieve the
                      edited instance (eg: {'pk': 12})
    @param model A django model class which implements the method get_related_entity().
    @param model title_format A format unicode with an arg (for the edited instance).
    @param can_change A function with instance and user as parameters, which
                      returns a Boolean: False causes a 403 error.
    """
    instance = get_object_or_404(model, **query_dict)
    user = request.user

    if can_change:
        if not can_change(instance, user):
            raise PermissionDenied(_('You can not edit this model'))
    elif isinstance(instance, models.CremeEntity):
        user.has_perm_to_change_or_die(instance)

    if request.method == 'POST':
        edit_form = form_class(user=user, data=request.POST, instance=instance,
                               files=request.FILES or None,
                              )

        if edit_form.is_valid():
            edit_form.save()
    else:  # return page on GET request
        edit_form = form_class(user=user, instance=instance)

    title_format = title_format or _(u'Edit «%s»')

    return inner_popup(request, template,
                       {'form':  edit_form,
                        'title': title_format % instance,
                        'submit_label': submit_label,
                       },
                       is_valid=edit_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                      )


class CremeModelEdition(base.CancellableMixin, base.PermissionsMixin, UpdateView):
    """ Base class for edition view with a form in Creme.
    You'll have to override at least the attributes 'model' & 'form_class'
    because the default ones are just abstract place-holders.

    The mandatory argument "user" of forms in Creme is filled.

    It manages the common UI of Creme Forms:
      - Title of the form
      - Label for the submit button
      - Cancel button.

    Notice that POST requests are managed within a SQL transaction,
    & the related instance is retrieved with a "SELECT ... FOR UPDATE",
    in order to serialize modifications correctly (eg: 2 form submissions
    at the same time won't causes some fields modifications of one form to
    be backed out by the 'initial' field value of the other form).
    """
    model = models.CremeModel
    form_class = forms.CremeModelForm
    template_name = 'creme_core/generics/blockform/edit.html'
    pk_url_kwarg = 'object_id'
    title = None  # None means a generic title is generated (see get_title()).
    submit_label = _('Save the modifications')

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.check_view_permissions(user=self.request.user)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.get_title()
        context['submit_label'] = self.get_submit_label()
        context['cancel_url'] = self.get_cancel_url()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user

        return kwargs

    def get_object(self, queryset=None):
        if self.request.method == 'POST':
            if queryset is None:
                queryset = self.get_queryset()

            return super().get_object(queryset=queryset.select_for_update())
        else:
            return super().get_object(queryset=queryset)

    def get_submit_label(self):
        return self.submit_label

    def get_title(self):
        title = self.title
        return ugettext('Edit «{}»').format(self.object) if title is None else title

    @atomic
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)


# TODO: assert model is an entity ?
class EntityEdition(CremeModelEdition):
    """ Base class to edit CremeEntities with a form.

    It's based on CremeModelEdition & adds the credentials checking.
    """
    model = models.CremeEntity
    form_class = forms.CremeEntityForm
    pk_url_kwarg = 'entity_id'

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_access_or_die(self.model._meta.app_label)

    def get_object(self, *args, **kwargs):
        entity = super().get_object(*args, **kwargs)
        self.request.user.has_perm_to_change_or_die(entity)

        return entity
