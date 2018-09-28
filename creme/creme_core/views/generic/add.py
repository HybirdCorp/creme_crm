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

from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView

from creme.creme_core import forms, models
from creme.creme_core.auth.decorators import login_required

from . import base, popup


def add_entity(request, form_class, url_redirect='',
               template='creme_core/generics/blockform/add.html',
               function_post_save=None, extra_initial=None, extra_template_dict=None):
    """
    @param url_redirect: string or format string with ONE argument replaced by the id of the created entity.
    @param function_post_save: allow processing on the just saved entity. Its signature: function_post_save(request, entity)
    """
    warnings.warn('creme_core.views.generic.add.add_entity() is deprecated ; '
                  'use the class-based views CremeModelCreation/EntityCreation instead.',
                  DeprecationWarning
                 )

    from django.http import HttpResponseRedirect
    from django.shortcuts import render

    from ..utils import build_cancel_path

    if request.method == 'POST':
        POST = request.POST
        entity_form = form_class(user=request.user, data=POST, files=request.FILES or None, initial=extra_initial)

        if entity_form.is_valid():
            entity_form.save()

            if function_post_save:
                function_post_save(request, entity_form.instance)

            if not url_redirect:
                url_redirect = entity_form.instance.get_absolute_url()
            elif url_redirect.find('%') > -1:  # NB: see header_filter.add
                url_redirect = url_redirect % entity_form.instance.id

            return HttpResponseRedirect(url_redirect)

        cancel_url = POST.get('cancel_url')
    else:  # GET
        entity_form = form_class(user=request.user, initial=extra_initial)
        cancel_url = build_cancel_path(request)

    model = form_class._meta.model
    template_dict = {'form':  entity_form,
                     'title': model.creation_label,
                     'submit_label': getattr(model, 'save_label', _('Save the entity')),
                     'cancel_url': cancel_url,
                    }

    if extra_template_dict:
        template_dict.update(extra_template_dict)

    return render(request, template, template_dict)


def add_to_entity(request, entity_id, form_class, title, entity_class=None, initial=None,
                  template='creme_core/generics/blockform/add_popup.html',
                  link_perm=False, submit_label=_('Save')):
    """ Add models related to one CremeEntity (eg: a CremeProperty)
    @param entity_id: Id of a CremeEntity.
    @param form_class: Form which __init__'s method MUST HAVE an argument caled 'entity' (the related CremeEntity).
    @param title: Title of the Inner Popup: Must be a format string with one arg: the related entity.
    @param entity_class: If given, it's the entity's class (else it could be any class inheriting CremeEntity).
    @param initial: Classical 'initial' of Forms.
    @param link_perm: Use LINK permission instead of CHANGE permission (default=False).
    """
    warnings.warn('creme_core.views.generic.add.add_to_entity() is deprecated ; '
                  'use the class-based view AddingToEntity instead.',
                  DeprecationWarning
                 )

    entity = get_object_or_404(entity_class, pk=entity_id) if entity_class else \
             get_object_or_404(models.CremeEntity, pk=entity_id).get_real_entity()
    user = request.user

    if link_perm:
        user.has_perm_to_link_or_die(entity)
    else:
        user.has_perm_to_change_or_die(entity)

    if request.method == 'POST':
        form = form_class(entity=entity, user=user, data=request.POST,
                          files=request.FILES or None, initial=initial,
                         )

        if form.is_valid():
            form.save()
    else:
        form = form_class(entity=entity, user=user, initial=initial)

    return popup.inner_popup(
        request, template,
        {'form':   form,
         'title':  title % entity,
         'submit_label': submit_label,
        },
        is_valid=form.is_valid(),
        reload=False,
        delegate_reload=True,
    )


def add_model_with_popup(request, form_class, title=None, initial=None,
                         template='creme_core/generics/blockform/add_popup.html',
                         submit_label=None):
    """
    @param title: Title of the Inner Popup.
    @param initial: Classical 'initial' of Forms (passed when the request is a GET).
    @param submit_label: Label of the submission button.
    """
    warnings.warn('creme_core.views.generic.add.add_model_with_popup() is deprecated ; '
                  'use the class-based view CremeModelCreationPopup instead.',
                  DeprecationWarning
                 )

    if request.method == 'POST':
        form = form_class(user=request.user, data=request.POST, files=request.FILES or None, initial=initial)

        if form.is_valid():
            form.save()
    else:
        form = form_class(user=request.user, initial=initial)

    try:
        model = form_class._meta.model
    except AttributeError:
        title = title or _('New')
        submit_label = submit_label or _('Save')
    else:
        title = title or getattr(model, 'creation_label', _('New'))
        submit_label = submit_label or getattr(model, 'save_label', _('Save'))

    return popup.inner_popup(
        request, template,
        {'form':         form,
         'title':        title,
         'submit_label': submit_label,
        },
        is_valid=form.is_valid(),
        reload=False,
        delegate_reload=True,
    )


# Class-based views  -----------------------------------------------------------

# TODO: add a system to be redirected from an argument "?next=" ?
class CremeModelCreation(base.CancellableMixin, base.PermissionsMixin, CreateView):
    """ Base class for creation view with a form in Creme.
    You'll have to override at least the attributes 'model' & 'form_class'
    because the default ones are just abstract place-holders.

    The mandatory argument "user" of forms in Creme is filled.

    It manages the common UI of Creme Forms:
      - Title of the form
      - Label for the submit button
      - Cancel button.

    Notice that POST requests are managed within a SQL transaction.
    """
    model = models.CremeModel  # TO BE OVERRIDDEN
    form_class = forms.CremeModelForm  # TO BE OVERRIDDEN
    template_name = 'creme_core/generics/blockform/add.html'
    title = None  # None means model.creation_label is used (see get_title()).
    submit_label = None  # None means model.save_label is used (see get_submit_label()).

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

    def get_title(self):
        title = self.title
        return self.model.creation_label if title is None else title

    def get_submit_label(self):
        label = self.submit_label
        return self.model.save_label if label is None else label

    @atomic
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)


# TODO: assert model is an entity ?
class EntityCreation(CremeModelCreation):
    """ Base class to create CremeEntities with a form.

    It's based on CremeModelCreation & adds the credentials checking.
    """
    model = models.CremeEntity
    form_class = forms.CremeEntityForm

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        model = self.model
        user.has_perm_to_access_or_die(model._meta.app_label)
        user.has_perm_to_create_or_die(model)


class CremeModelCreationPopup(popup.InnerPopupMixin, CremeModelCreation):
    """ Base class for creation view with a form in Creme within an Inner-Popup.
    See CremeModelCreation.
    """
    # model = models.CremeModel  # TO BE OVERRIDDEN
    # form_class = forms.CremeModelForm  # TO BE OVERRIDDEN
    template_name = 'creme_core/generics/blockform/add_popup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_inner_popup'] = True  # TODO: in new base popup when including ?
        context['persisted'] = self.get_persisted()  # TODO: remove from form-templates ?

        return context

    def get_success_url(self):
        return ''

    def form_valid(self, form):
        super().form_valid(form)
        return self.render_to_response(self.get_context_data(form=form))

    def render_to_response(self, context, **response_kwargs):
        from django.shortcuts import render

        request = self.request

        return render(request=request,
                      template_name='creme_core/generics/inner_popup.html',
                      context=self.get_popup_context(context),
                     )


class AddingToEntity(base.EntityRelatedMixin, CremeModelCreationPopup):
    """ This specialisation of CremeModelCreationPopup creates some model
    instances related to a CremeEntity.

    Attributes:
    entity_form_kwarg: The related entity is given to the form with this name.
                       ('entity' by default).
                       <None> means the entity is not passed to the form.
    """
    entity_form_kwarg = 'entity'
    title_format = None  # If a {}-format string is given, it's used to built
                         # the title with the related entity as argument (see get_title())

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        entity_classes = self.entity_classes
        if entity_classes is not None:
            has_perm = user.has_perm_to_access_or_die

            if isinstance(entity_classes, (list, tuple)):  # Sequence of classes
                for app_label in {c._meta.app_label for c in entity_classes}:
                    has_perm(app_label)
            else:  # CremeEntity sub-model
                has_perm(entity_classes._meta.app_label)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        entity = self.get_related_entity()
        if self.entity_form_kwarg:
            kwargs[self.entity_form_kwarg] = entity

        return kwargs

    def get_title_format(self):
        return self.title_format

    def get_title(self):
        title_format = self.get_title_format()

        return title_format.format(self.get_related_entity()
                                       .allowed_str(self.request.user)
                                  ) \
               if title_format is not None else\
               super().get_title()
