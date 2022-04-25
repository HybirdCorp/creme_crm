# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
from django.utils.translation import gettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import UpdateView

from creme.creme_core import forms, models
from creme.creme_core.gui.custom_form import CustomFormDescriptor

from . import base


class CremeEdition(base.CremeFormView):
    template_name = 'creme_core/generics/blockform/edit.html'
    title = _('Edit')
    submit_label = _('Save the modifications')


class CremeEditionPopup(base.CremeFormPopup):
    template_name = 'creme_core/generics/blockform/edit-popup.html'
    title = _('Edit')
    submit_label = _('Save the modifications')


class CremeModelEdition(base.CustomFormMixin,
                        base.CancellableMixin,
                        base.CallbackMixin,
                        base.PermissionsMixin,
                        base.TitleMixin,
                        base.SubmittableMixin,
                        UpdateView):
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
    form_class: Union[Type[BaseForm], CustomFormDescriptor] = forms.CremeModelForm
    template_name = 'creme_core/generics/blockform/edit.html'
    pk_url_kwarg = 'object_id'
    title = _('Edit «{object}»')
    submit_label = _('Save the modifications')

    def check_instance_permissions(self, instance, user):
        pass

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

    def get_object(self, queryset=None):
        request = self.request

        if request.method == 'POST':
            if queryset is None:
                queryset = self.get_queryset()

            instance = super().get_object(queryset=queryset.select_for_update())
        else:
            instance = super().get_object(queryset=queryset)

        self.check_instance_permissions(instance, request.user)

        return instance

    def get_success_url(self):
        return self.get_callback_url() or super().get_success_url()

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['object'] = self.object

        return data

    @atomic
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)


# TODO: assert model is an entity ?
class EntityEdition(CremeModelEdition):
    """ Base class to edit CremeEntities with a form.

    It's based on CremeModelEdition & adds the credentials checking.
    """
    model = models.CremeEntity
    form_class: Union[Type[BaseForm], CustomFormDescriptor] = forms.CremeEntityForm
    pk_url_kwarg = 'entity_id'

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_change_or_die(instance)

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_access_or_die(self.model._meta.app_label)


# TODO: factorise with CremeModelCreationPopup ?
@method_decorator(xframe_options_sameorigin, name='dispatch')
class CremeModelEditionPopup(CremeModelEdition):
    """ Base class for edition view with a form in Creme within an Inner-Popup.
    See CremeModelEdition.
    """
    # model = models.CremeModel  # TO BE OVERRIDDEN
    # form_class = forms.CremeModelForm  # TO BE OVERRIDDEN
    template_name = 'creme_core/generics/blockform/edit-popup.html'

    def get_success_url(self):
        return ''

    def form_valid(self, form):
        self.object = form.save()

        return HttpResponse(self.get_success_url(), content_type='text/plain')


class EntityEditionPopup(CremeModelEditionPopup):
    """ Base class to edit CremeEntities with a form in an Inner-Popup.

    It's based on CremeModelEditionPopup & adds the credentials checking.
    """
    model = models.CremeEntity
    form_class: Union[Type[BaseForm], CustomFormDescriptor] = forms.CremeEntityForm
    pk_url_kwarg = 'entity_id'

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_change_or_die(instance)

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_access_or_die(self.model._meta.app_label)


class RelatedToEntityEditionPopup(base.EntityRelatedMixin, CremeModelEditionPopup):
    """ This specialisation of CremeModelEditionPopup is made to edit an instance
    of model related to a CremeEntity instance.

    This model must have a method 'get_related_entity()'.

    NB: get_title_format_data() injects the related entity with key "entity".
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.related_entity = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.set_entity_in_form_kwargs(kwargs)

        return kwargs

    def get_related_entity(self):
        entity = self.related_entity

        if entity is None:
            entity = self.object.get_related_entity()
            self.check_related_entity_permissions(entity=entity, user=self.request.user)

            self.related_entity = entity

        return entity

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['entity'] = self.get_related_entity().allowed_str(self.request.user)

        return data
