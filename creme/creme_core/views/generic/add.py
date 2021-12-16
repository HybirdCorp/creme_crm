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

from typing import Type, Union

from django.db.transaction import atomic
from django.forms.forms import BaseForm
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import CreateView

from creme.creme_core import forms, models
from creme.creme_core.gui.custom_form import CustomFormDescriptor

from . import base


# TODO: add a system to be redirected after the creation (from an argument "?next=") ?
class CremeModelCreation(base.CustomFormMixin,
                         base.CancellableMixin,
                         base.CallbackMixin,
                         base.PermissionsMixin,
                         base.TitleMixin,
                         base.SubmittableMixin,
                         CreateView):
    """ Base class for creation view with a model-form in Creme.
    You'll have to override at least the attributes 'model' & 'form_class'
    because the default ones are just abstract place-holders.

    The mandatory argument "user" of forms in Creme is filled.

    It manages the common UI of Creme Forms:
      - Title of the form
      - Label for the submit button
      - Cancel button.

    Attributes:
      - atomic_POST: <True> (default value means that POST requests are
                     managed within a SQL transaction.

    Notes :
    submit_label: <None> (default value) means that <model.save_label> is used.
    """
    model = models.CremeModel  # TO BE OVERRIDDEN
    # TO BE OVERRIDDEN
    form_class: Union[Type[BaseForm], CustomFormDescriptor] = forms.CremeModelForm
    template_name = 'creme_core/generics/blockform/add.html'
    title = '{creation_label}'
    submit_label = None
    atomic_POST = True

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return self.handle_not_logged()

        self.check_view_permissions(user=user)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.get_title()
        context['submit_label'] = self.get_submit_label()

        # TODO: pass 'self.cancel_url_post_argument' to name the input?
        context['cancel_url'] = self.get_cancel_url()

        context['callback_url'] = cb_url = self.get_callback_url()
        if cb_url:
            context['callback_url_name'] = self.callback_url_argument

        return context

    def get_form_class(self):
        return self.get_custom_form_class(super().get_form_class())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user

        return kwargs

    def get_success_url(self):
        return self.get_callback_url() or super().get_success_url()

    def get_submit_label(self):
        return super().get_submit_label() or self.model.save_label

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['creation_label'] = self.model.creation_label

        return data

    def post(self, *args, **kwargs):
        if self.atomic_POST:
            with atomic():  # TODO: durable=True ? (+ other generic views)
                return super().post(*args, **kwargs)
        else:
            return super().post(*args, **kwargs)


# TODO: assert model is an entity ?
class EntityCreation(CremeModelCreation):
    """ Base class to create CremeEntities with a form.

    It's based on CremeModelCreation & adds the credentials checking.
    """
    model = models.CremeEntity
    form_class: Union[Type[forms.CremeEntityForm], CustomFormDescriptor] = forms.CremeEntityForm

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        model = self.model
        user.has_perm_to_access_or_die(model._meta.app_label)
        user.has_perm_to_create_or_die(model)


@method_decorator(xframe_options_sameorigin, name='dispatch')
class CremeModelCreationPopup(CremeModelCreation):
    """ Base class for creation view with a form in Creme within an Inner-Popup.
    See CremeModelCreation.
    """
    # model = models.CremeModel  # TO BE OVERRIDDEN
    # form_class = forms.CremeModelForm  # TO BE OVERRIDDEN
    template_name = 'creme_core/generics/blockform/add-popup.html'

    def get_success_url(self):
        return ''

    def form_valid(self, form):
        self.object = form.save()

        return HttpResponse(self.get_success_url(), content_type='text/plain')


class EntityCreationPopup(CremeModelCreationPopup):
    model = models.CremeEntity
    form_class: Union[Type[forms.CremeEntityForm], CustomFormDescriptor] = forms.CremeEntityForm

    # TODO: factorise
    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        model = self.model
        user.has_perm_to_access_or_die(model._meta.app_label)
        user.has_perm_to_create_or_die(model)


class AddingInstanceToEntityPopup(base.EntityRelatedMixin,
                                  CremeModelCreationPopup):
    """ This specialisation of CremeModelCreationPopup creates an instance
    related to a CremeEntity.

    NB: get_title_format_data() injects the related entity with key "entity".
    """
    title = '{entity}'

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        self.check_entity_classes_apps(user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.set_entity_in_form_kwargs(kwargs)

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['entity'] = self.get_related_entity().allowed_str(self.request.user)

        return data
