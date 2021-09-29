# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2021  Hybird
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

import logging
from typing import List, Type, Union

from django.core.exceptions import ImproperlyConfigured
from django.db.transaction import atomic
from django.forms import BaseForm, ModelForm
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.generic.detail import SingleObjectMixin
from formtools.wizard.views import SessionWizardView

from creme.creme_core import models
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.creme_core.models import CustomFormConfigItem

from . import base

logger = logging.getLogger(__name__)


class CremeWizardView(base.PermissionsMixin,
                      base.TitleMixin,
                      base.SubmittableMixin,
                      SessionWizardView):
    """ Base class for wizard view in Creme.
    You'll have to override at least the attributes 'form_list' & 'success_url'
    because the default ones are just abstract place-holders.

    The mandatory argument "user" of forms in Creme is filled.

    It manages the common UI of Creme Forms:
      - Title of the form
      - Label for the submit button

    Attributes:
      - form_list: list of form classes or CustomFormDescriptor instances ;
                   each one is used for a step
                   (see <formtools.wizard.views.SessionWizardView>).
      - atomic_POST: <True> (default value means that POST requests are
                     managed within a SQL transaction.
      - success_url: django's generic-views-like attribute for redirection URL
                     used after the successful validation of the final step.
      - step_first_label: label used for the "First step" button.
      - step_prev_label: label used for the "Previous step" button.
      - step_next_label: label used for the "Next step" button.

    Notes :
    The form classes in the attribute "form_list" can have the following
    attributes :
      - step_prev_label
      - step_first_label
      - submit_label
    If they contain a non-empty value, their value override the corresponding
    general attribute of the view.
    """
    form_list: List[Union[Type[BaseForm], CustomFormDescriptor]]  # = [...]  # TO BE OVERRIDDEN
    template_name = 'creme_core/generics/blockform/add-wizard.html'
    atomic_POST = True
    success_url = None
    step_first_label = _('First step')
    step_prev_label = _('Previous step')
    step_next_label = _('Next step')

    @classmethod
    def get_initkwargs(cls, form_list=None, *args, **kwargs):
        raw_form_list = form_list or kwargs.pop('form_list', getattr(cls, 'form_list', None)) or []

        # NB: SessionWizardView.get_initkwargs() needs that <form_list> elements
        #     are form classes (final ones, with the attribute "base_fields"),
        #     & SessionWizardView does have a method get_form_class() to
        #     dynamically build form classes form CustomFormDescriptor
        #     => we use a proxy system.
        def _wrap_custom_form(descriptor):
            class _CustomFormProxy(ModelForm):
                class Meta:
                    model = descriptor.model
                    fields = ()

                def __new__(inner_cls, *inner_args, **inner_kwargs):
                    # return descriptor.build_form_class()(*inner_args, **inner_kwargs)
                    try:
                        form_cls = descriptor.build_form_class(
                            item=CustomFormConfigItem.objects.get_for_user(
                                descriptor=descriptor,
                                user=inner_kwargs['user'],
                            ),
                        )
                    except CustomFormConfigItem.DoesNotExist as e:
                        # TODO: unit test
                        raise Http404(
                            gettext(
                                'No default form has been created in DataBase for the '
                                'model «{model}». Contact your administrator.'
                            ).format(model=descriptor.model._meta.verbose_name)
                        ) from e

                    return form_cls(*inner_args, **inner_kwargs)

            return _CustomFormProxy

        return super().get_initkwargs(
            form_list=[
                _wrap_custom_form(form_info)
                if isinstance(form_info, CustomFormDescriptor)
                else form_info  # NB: form class case
                for form_info in raw_form_list
            ],
            *args, **kwargs
        )

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return self.handle_not_logged()

        self.check_view_permissions(user=user)

        return super().dispatch(request, *args, **kwargs)

    def post(self, *args, **kwargs):
        if kwargs.get('atomic_POST', self.atomic_POST):
            with atomic():
                return super().post(*args, **kwargs)
        else:
            return super().post(*args, **kwargs)

    def done_save(self, form_list):
        # We save the last form
        next(reversed(form_list)).save()

    def done(self, form_list, **kwargs):
        self.done_save(form_list=form_list)

        return HttpResponseRedirect(self.get_success_url(form_list=form_list))

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context['title'] = getattr(form, 'step_title', '') or self.get_title()
        context['help_message'] = getattr(form, 'step_help_message', '')

        context['prev_label']  = getattr(form, 'step_prev_label',  self.step_prev_label)
        context['first_label'] = getattr(form, 'step_first_label', self.step_first_label)

        submit_label = getattr(form, 'step_submit_label', '')
        if not submit_label:
            submit_label = (
                self.get_submit_label()
                if int(self.steps.current) + 1 == len(self.form_list) else
                self.step_next_label
            )
        context['submit_label'] = submit_label

        return context

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user

        return kwargs

    def get_success_url(self, form_list):
        """Return the URL to redirect to after processing a valid last form."""
        if not self.success_url:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")

        return str(self.success_url)  # success_url may be lazy

    def validate_previous_steps(self, step):
        i_prev_step = int(step) - 1

        if i_prev_step >= 0:
            prev_step = str(i_prev_step)
            form_obj = self.get_form(
                step=prev_step,
                data=self.storage.get_step_data(prev_step),
                files=self.storage.get_step_files(prev_step),
            )
            if not form_obj.is_valid():
                logger.warning(
                    '%s.validate_previous_steps(): the form <%s> is not valid '
                    '(maybe it is not re-entrant with a cleaned instance).'
                    'Errors: %s',
                    type(self).__name__,
                    type(form_obj).__name__,
                    form_obj.errors,
                )


class CremeWizardViewPopup(CremeWizardView):
    """ Base class for wizard view in Creme within an Inner-Popup.
    See CremeWizardView.
    """
    template_name = 'creme_core/generics/blockform/add-wizard-popup.html'

    def get_success_url(self, form_list):
        return ''

    def done(self, form_list, **kwargs):
        self.done_save(form_list=form_list)

        return HttpResponse(
            self.get_success_url(form_list=form_list),
            content_type='text/plain',
        )


# Creation ---------------------------------------------------------------------

class CremeModelCreationWizard(CremeWizardView):
    """ Base class for creating an instance with a wizard view.

    You'll have to override at least the attributes 'model' & 'form_list' (see
    CremeWizardView).

    Attributes:
      - model: class inheriting <creme_core.models.CremeModel>.

    Notes :
    submit_label: <None> (default value) means that <model.save_label> is used.
    """
    model = models.CremeModel  # TO BE OVERRIDDEN
    title = '{creation_label}'
    submit_label = None

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['creation_label'] = self.model.creation_label

        return data

    def get_submit_label(self):
        return super().get_submit_label() or self.model.save_label

    def get_success_url(self, form_list):
        try:
            url = next(reversed(form_list)).instance.get_absolute_url()
        except AttributeError:
            url = None

        return url or super().get_success_url(form_list=form_list)


class EntityCreationWizard(CremeModelCreationWizard):
    """ Base class to create CremeEntities with a wizard.

    It's based on CremeModelCreationWizard & adds the credentials checking.
    """
    model = models.CremeEntity  # TO BE OVERRIDDEN

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        model = self.model
        user.has_perm_to_access_or_die(model._meta.app_label)
        user.has_perm_to_create_or_die(model)


class CremeModelCreationWizardPopup(CremeModelCreationWizard):
    """ Base class for creating an instance with a wizard view within an
    Inner-Popup.

    See CremeModelCreationWizard.
    """
    template_name = 'creme_core/generics/blockform/add-wizard-popup.html'

    def get_success_url(self, form_list):
        return ''

    def done(self, form_list, **kwargs):
        self.done_save(form_list=form_list)

        return HttpResponse(
            self.get_success_url(form_list=form_list),
            content_type='text/plain',
        )


class EntityCreationWizardPopup(CremeModelCreationWizardPopup):
    """ Base class to create CremeEntities with a wizard within an Inner-Popup.

    It's based on CremeModelCreationWizardPopup & adds the credentials checking.
    """
    model = models.CremeEntity  # TO BE OVERRIDDEN

    # TODO: factorise
    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        model = self.model
        user.has_perm_to_access_or_die(model._meta.app_label)
        user.has_perm_to_create_or_die(model)


# Edition ---------------------------------------------------------------------


class CremeModelEditionWizard(SingleObjectMixin, CremeWizardView):
    """ Base class for editing an instance with a wizard view.

    You'll have to override at least the attributes 'model' & 'form_list' (see
    CremeWizardView) because the default ones are just abstract place-holders.

    Attributes:
      - model: class inheriting <creme_core.models.CremeModel>.
      - queryset: instance of <django.db.models.query.QuerySet> used to filter
                  the results when retrieving the edited instance (see
                  <django.views.generic.detail.SingleObjectMixin>).
      - pk_url_kwarg: see SingleObjectMixin.

    Notice that POST requests are managed within a SQL transaction,
    & the related instance is retrieved with a "SELECT ... FOR UPDATE",
    in order to serialize modifications correctly (eg: 2 form submissions
    at the same time won't causes some fields modifications of one form to
    be backed out by the 'initial' field value of the other form).
    """
    model = models.CremeModel  # TO BE OVERRIDDEN
    queryset = None
    template_name = 'creme_core/generics/blockform/edit-wizard.html'
    pk_url_kwarg = 'object_id'
    title = _('Edit «{object}»')
    submit_label = _('Save the modifications')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.object = None

    def check_instance_permissions(self, instance, user):
        pass

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, *args, **kwargs):
        if kwargs.get('atomic_POST', self.atomic_POST):
            with atomic():
                self.object = self.get_object()
                return super().post(atomic_POST=False, *args, **kwargs)
        else:
            self.object = self.get_object()
            return super().post(atomic_POST=False, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = CremeWizardView.get_context_data(self, form=form, **kwargs)

        # NB: Does not work (diamond calls...)
        # context.update(SingleObjectMixin.get_context_data(self))

        instance = self.object
        if instance:
            context['object'] = instance
            context_object_name = self.get_context_object_name(instance)

            if context_object_name:
                context[context_object_name] = instance

        return context

    def get_form_instance(self, step):
        instance = super().get_form_instance(step=step) or self.object

        # We fill the instance with the previous step
        # (so recursively all previous should be used)
        self.validate_previous_steps(step)

        return instance

    def get_object(self, queryset=None):
        request = self.request

        if request.method == 'POST':
            if queryset is None:
                queryset = self.get_queryset()

            instance = super().get_object(queryset=queryset.select_for_update())
        else:
            instance = super().get_object(queryset=queryset)

        self.check_instance_permissions(instance=instance, user=request.user)

        return instance

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['object'] = self.object

        return data


class EntityEditionWizard(CremeModelEditionWizard):  # TODO: test
    """ Base class to edit CremeEntities with a wizard.

    It's based on CremeModelEditionWizard & adds the credentials checking.
    """
    model = models.CremeEntity  # TO BE OVERRIDDEN
    pk_url_kwarg = 'entity_id'

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_change_or_die(instance)

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_access_or_die(self.model._meta.app_label)


class CremeModelEditionWizardPopup(CremeModelEditionWizard):
    """ Base class for editing an instance with a wizard view within an
    Inner-Popup.

    See CremeModelEditionWizard.
    """
    template_name = 'creme_core/generics/blockform/edit-wizard-popup.html'

    def get_success_url(self, form_list):
        return ''

    def done(self, form_list, **kwargs):
        self.done_save(form_list=form_list)

        return HttpResponse(
            self.get_success_url(form_list=form_list),
            content_type='text/plain',
        )


class EntityEditionWizardPopup(CremeModelEditionWizard):  # TODO: test
    """ Base class to edit CremeEntities with a wizard in an Inner-Popup..

    It's based on CremeModelEditionWizard & adds the credentials checking.
    """
    model = models.CremeEntity
    pk_url_kwarg = 'entity_id'

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_change_or_die(instance)

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_access_or_die(self.model._meta.app_label)
