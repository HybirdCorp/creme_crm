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

from django.db.transaction import atomic
from django.http import HttpResponse
# from django.shortcuts import get_object_or_404
# from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView

from creme.creme_core import forms, models

from . import base  # popup


# def add_entity(request, form_class, url_redirect='',
#                template='creme_core/generics/blockform/add.html',
#                function_post_save=None, extra_initial=None, extra_template_dict=None):
#     """
#     @param url_redirect: string or format string with ONE argument replaced by the id of the created entity.
#     @param function_post_save: allow processing on the just saved entity. Its signature: function_post_save(request, entity)
#     """
#     warnings.warn('creme_core.views.generic.add.add_entity() is deprecated ; '
#                   'use the class-based views CremeModelCreation/EntityCreation instead.',
#                   DeprecationWarning
#                  )
#
#     from django.http import HttpResponseRedirect
#     from django.shortcuts import render
#
#     from ..utils import build_cancel_path
#
#     if request.method == 'POST':
#         POST = request.POST
#         entity_form = form_class(user=request.user, data=POST, files=request.FILES or None, initial=extra_initial)
#
#         if entity_form.is_valid():
#             entity_form.save()
#
#             if function_post_save:
#                 function_post_save(request, entity_form.instance)
#
#             if not url_redirect:
#                 url_redirect = entity_form.instance.get_absolute_url()
#             elif url_redirect.find('%') > -1:  # NB: see header_filter.add
#                 url_redirect = url_redirect % entity_form.instance.id
#
#             return HttpResponseRedirect(url_redirect)
#
#         cancel_url = POST.get('cancel_url')
#     else:  # GET
#         entity_form = form_class(user=request.user, initial=extra_initial)
#         cancel_url = build_cancel_path(request)
#
#     model = form_class._meta.model
#     template_dict = {'form':  entity_form,
#                      'title': model.creation_label,
#                      'submit_label': getattr(model, 'save_label', _('Save the entity')),
#                      'cancel_url': cancel_url,
#                     }
#
#     if extra_template_dict:
#         template_dict.update(extra_template_dict)
#
#     return render(request, template, template_dict)


# def add_to_entity(request, entity_id, form_class, title, entity_class=None, initial=None,
#                   template='creme_core/generics/blockform/add_popup.html',
#                   link_perm=False, submit_label=_('Save')):
#     """ Add models related to one CremeEntity (eg: a CremeProperty)
#     @param entity_id: Id of a CremeEntity.
#     @param form_class: Form which __init__'s method MUST HAVE an argument caled 'entity' (the related CremeEntity).
#     @param title: Title of the Inner Popup: Must be a format string with one arg: the related entity.
#     @param entity_class: If given, it's the entity's class (else it could be any class inheriting CremeEntity).
#     @param initial: Classical 'initial' of Forms.
#     @param link_perm: Use LINK permission instead of CHANGE permission (default=False).
#     """
#     warnings.warn('creme_core.views.generic.add.add_to_entity() is deprecated ; '
#                   'use the class-based view AddingToEntity instead.',
#                   DeprecationWarning
#                  )
#
#     entity = get_object_or_404(entity_class, pk=entity_id) if entity_class else \
#              get_object_or_404(models.CremeEntity, pk=entity_id).get_real_entity()
#     user = request.user
#
#     if link_perm:
#         user.has_perm_to_link_or_die(entity)
#     else:
#         user.has_perm_to_change_or_die(entity)
#
#     if request.method == 'POST':
#         form = form_class(entity=entity, user=user, data=request.POST,
#                           files=request.FILES or None, initial=initial,
#                          )
#
#         if form.is_valid():
#             form.save()
#     else:
#         form = form_class(entity=entity, user=user, initial=initial)
#
#     return popup.inner_popup(
#         request, template,
#         {'form':   form,
#          'title':  title % entity,
#          'submit_label': submit_label,
#         },
#         is_valid=form.is_valid(),
#         reload=False,
#         delegate_reload=True,
#     )


# def add_model_with_popup(request, form_class, title=None, initial=None,
#                          template='creme_core/generics/blockform/add_popup.html',
#                          submit_label=None):
#     """
#     @param title: Title of the Inner Popup.
#     @param initial: Classical 'initial' of Forms (passed when the request is a GET).
#     @param submit_label: Label of the submission button.
#     """
#     warnings.warn('creme_core.views.generic.add.add_model_with_popup() is deprecated ; '
#                   'use the class-based view CremeModelCreationPopup instead.',
#                   DeprecationWarning
#                  )
#
#     if request.method == 'POST':
#         form = form_class(user=request.user, data=request.POST, files=request.FILES or None, initial=initial)
#
#         if form.is_valid():
#             form.save()
#     else:
#         form = form_class(user=request.user, initial=initial)
#
#     try:
#         model = form_class._meta.model
#     except AttributeError:
#         title = title or _('New')
#         submit_label = submit_label or _('Save')
#     else:
#         title = title or getattr(model, 'creation_label', _('New'))
#         submit_label = submit_label or getattr(model, 'save_label', _('Save'))
#
#     return popup.inner_popup(
#         request, template,
#         {'form':         form,
#          'title':        title,
#          'submit_label': submit_label,
#         },
#         is_valid=form.is_valid(),
#         reload=False,
#         delegate_reload=True,
#     )


# Class-based views  -----------------------------------------------------------

# TODO: add a system to be redirected after the creation (from an argument "?next=") ?
class CremeModelCreation(base.CancellableMixin,
                         base.PermissionsMixin,
                         base.TitleMixin,
                         base.SubmittableMixin,
                         CreateView,
                        ):
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
    form_class = forms.CremeModelForm  # TO BE OVERRIDDEN
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
        context['cancel_url'] = self.get_cancel_url()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['creation_label'] = self.model.creation_label

        return data

    def get_submit_label(self):
        return super().get_submit_label() or self.model.save_label

    def post(self, *args, **kwargs):
        if self.atomic_POST:
            with atomic():
                return super().post(*args, **kwargs)
        else:
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


class CremeModelCreationPopup(CremeModelCreation):
    """ Base class for creation view with a form in Creme within an Inner-Popup.
    See CremeModelCreation.
    """
    # model = models.CremeModel  # TO BE OVERRIDDEN
    # form_class = forms.CremeModelForm  # TO BE OVERRIDDEN
    # template_name = 'creme_core/generics/blockform/add_popup.html'  # DO NOT USE OLD TEMPLATES !!!
    template_name = 'creme_core/generics/blockform/add-popup.html'

    def get_success_url(self):
        return ''

    def form_valid(self, form):
        self.object = form.save()

        return HttpResponse(self.get_success_url(), content_type='text/plain')


class EntityCreationPopup(CremeModelCreationPopup):
    model = models.CremeEntity
    form_class = forms.CremeEntityForm

    # TODO: factorise
    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        model = self.model
        user.has_perm_to_access_or_die(model._meta.app_label)
        user.has_perm_to_create_or_die(model)


class AddingInstanceToEntityPopup(base.EntityRelatedMixin, CremeModelCreationPopup):
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
