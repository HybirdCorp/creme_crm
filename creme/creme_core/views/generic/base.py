# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2019  Hybird
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

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _, gettext
from django.views import generic as django_generic

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import CremeForm
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import get_ct_or_404

from ..utils import build_cancel_path


class CancellableMixin:
    """Mixin that helps building an URL to go back when the user is in a form."""
    cancel_url_post_argument = 'cancel_url'

    def get_cancel_url(self):
        request = self.request
        return request.POST.get(self.cancel_url_post_argument) \
               if request.method == 'POST' else \
               build_cancel_path(request)


# NB: we do not use 'django.contrib.auth.mixins.AccessMixin' because its API would
#     be confusing with ours (eg: handle_no_permission() & get_permission_denied_message()
#     are only about logging-in, while we have check_view_permissions()...)
class PermissionsMixin:
    """Mixin that helps checking the global permission of a view.
    The needed permissions are stored in the attribute <permissions>, an could be:
      - a string. Eg:
          permissions = 'my_app'
      - a sequence of strings. Eg:
          permissions = ['my_app1', 'my_app2.can_admin']
      - <None> (default value) means no permission is checked.
    """
    login_url_name = None
    login_redirect_arg_name = REDIRECT_FIELD_NAME
    permissions = None

    def check_view_permissions(self, user):
        """Check global permission of the view.

        @param user: Instance of <auth.get_user_model()>.
        @raise: PermissionDenied.
        """
        permissions = self.permissions

        # if permissions is not None:
        if permissions:
            # TODO: has_perm[s]_or_die() with better error message ?
            allowed = user.has_perm(permissions) \
                      if isinstance(permissions, str) else \
                      user.has_perms(permissions)

            if not allowed:
                raise PermissionDenied(gettext('You are not allowed to access this view.'))

    def handle_not_logged(self):
        return HttpResponseRedirect(self.get_login_uri())

    def get_login_uri(self):
        """Get the URI where to redirect anonymous users."""
        login_url_name = self.login_url_name or settings.LOGIN_URL
        if not login_url_name:
            raise ImproperlyConfigured('Define settings.LOGIN_URL')

        url = reverse(login_url_name)
        redirect_arg_name = self.login_redirect_arg_name

        return '{}?{}'.format(
                    url,
                    urlencode({redirect_arg_name: self.request.get_full_path()}, safe='/'),
                ) if redirect_arg_name else url


class EntityRelatedMixin:
    """Mixin which help building view which retrieve a CremeEntity instance,
    in order to add it some additional data (generally stored in an object
    referencing this entity).

    Attributes:
    entity_id_url_kwarg: string indicating the name of the key-word
        (ie <self.kwargs>) which stores the ID oh the related entity.
    entity_classes: it can be:
        - None => that all model of CremeEntity are accepted ; a second query
         is done to retrieve the real entity.
        - a class (inheriting <CremeEntity>) => only entities of this class are
          retrieved (& 1 query is done, not 2, to retrieve it).
        - a sequence (list/tuple) of classes (inheriting <CremeEntity>) => only
          entities of one of these classes are accepted ; a second query is done
          to retrieve the real entity if the class is accepted.
    entity_form_kwarg: The related entity is given to the form with this name
        when set_entity_in_form_kwargs() is called (views with form only).
        ('entity' by default).
        <None> means the entity is not passed to the form.

    Tips: override <check_related_entity_permissions()> if you want to check
    LINK permission instead of CHANGE.
    """
    entity_id_url_kwarg = 'entity_id'
    entity_classes = None
    entity_form_kwarg = 'entity'

    def check_related_entity_permissions(self, entity, user):
        """ Check the permissions of the related entity which just has been retrieved.

        @param entity: Instance of model inheriting CremeEntity.
        @param user: Instance of <auth.get_user_model()>.
        @raise: PermissionDenied.
        """
        user.has_perm_to_change_or_die(entity)

    def check_entity_classes_apps(self, user):
        entity_classes = self.entity_classes

        if entity_classes is not None:
            has_perm = user.has_perm_to_access_or_die

            if isinstance(entity_classes, (list, tuple)):  # Sequence of classes
                for app_label in {c._meta.app_label for c in entity_classes}:
                    has_perm(app_label)
            else:  # CremeEntity sub-model
                has_perm(entity_classes._meta.app_label)

    def get_related_entity_id(self):
        return self.kwargs[self.entity_id_url_kwarg]

    def get_related_entity(self):
        """Retrieves the real related entity at the first call, then returns
        the cached object.
        @return: An instance of "real" entity.
        """
        try:
            entity = getattr(self, 'related_entity')
        except AttributeError:
            entity_classes = self.entity_classes
            entity_id = self.get_related_entity_id()

            if entity_classes is None:
                entity = get_object_or_404(CremeEntity, id=entity_id).get_real_entity()
            elif isinstance(entity_classes, (list, tuple)):  # Sequence of classes
                get_for_ct = ContentType.objects.get_for_model
                entity = get_object_or_404(
                    CremeEntity,
                    id=entity_id,
                    entity_type__in=[get_for_ct(c) for c in entity_classes],
                ).get_real_entity()
            else:
                assert issubclass(entity_classes, CremeEntity)
                entity = get_object_or_404(entity_classes, pk=entity_id)

            self.check_related_entity_permissions(entity=entity, user=self.request.user)

            self.related_entity = entity

        return entity

    def set_entity_in_form_kwargs(self, form_kwargs):
        entity = self.get_related_entity()

        if self.entity_form_kwarg:
            form_kwargs[self.entity_form_kwarg] = entity


class ContentTypeRelatedMixin:
    """Mixin for views which retrieve a ContentType from an URL argument.

    Attributes:
    ctype_id_url_kwarg: string indicating the name of the key-word (ie <self.kwargs>)
                        which stores the ID oh the ContentType instance.
    ct_id_0_accepted: boolean (False by default). "True" indicates that the
                      ID retrieve if the URL can be "0" (& so get_ctype() will
                      returns <None> -- instead of a 404 error).
    """
    ctype_id_url_kwarg = 'ct_id'
    ct_id_0_accepted = False

    def check_related_ctype(self, ctype):
        pass

    def get_ctype_id(self):
        return self.kwargs[self.ctype_id_url_kwarg]

    def get_ctype(self):
        try:
            ctype = getattr(self, 'related_ctype')
        except AttributeError:
            ct_id_str = self.get_ctype_id()

            try:
                ct_id = int(ct_id_str)
            except ValueError:
                raise Http404('ContentType ID must be an integer.')

            if self.ct_id_0_accepted and not ct_id:
                ctype = None
            else:
                ctype = get_ct_or_404(ct_id)

                self.check_related_ctype(ctype)

            self.related_ctype = ctype

        return ctype


class EntityCTypeRelatedMixin(ContentTypeRelatedMixin):
    """Specialisation of ContentTypeRelatedMixin to retrieve a ContentType
    related to a CremeEntity child class.
    """
    def check_related_ctype(self, ctype):
        self.request.user.has_perm_to_access_or_die(ctype.app_label)

        model = ctype.model_class()
        if not issubclass(model, CremeEntity):
            raise ConflictError('This model is not a entity model: {}'.format(model))


class CheckedView(PermissionsMixin, django_generic.View):
    """Creme version of the django's View ; it checked that the
    user is logged & has some permission.
    """
    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return self.handle_not_logged()

        self.check_view_permissions(user=user)

        return super().dispatch(request, *args, **kwargs)


class CheckedTemplateView(PermissionsMixin, django_generic.TemplateView):
    """Creme version of the django's TemplateView ; it checked that the
    user is logged & has some permission.
    """
    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return self.handle_not_logged()

        self.check_view_permissions(user=user)

        return super().dispatch(request, *args, **kwargs)


class BricksMixin:
    """Mixin for views which use Bricks for they display.

    Attributes:
    brick_registry: Instance of _BrickRegistry, used to retrieve the instances
                    of Bricks from their ID (see get_brick_ids() & get_bricks()).
    bricks_reload_url_name: Name of the URL used to relaod the bricks
                            (see get_bricks_reload_url()).
    """
    brick_registry = brick_registry
    bricks_reload_url_name = 'creme_core__reload_bricks'

    def get_brick_ids(self):
        return ()

    def get_bricks(self):
        return list(self.brick_registry.get_bricks(
            [id_ for id_ in self.get_brick_ids() if id_]
        ))

    def get_bricks_reload_url(self):
        name = self.bricks_reload_url_name
        return reverse(name) if name else ''


class BricksView(BricksMixin, CheckedTemplateView):
    """Base view which uses Bricks for its display."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bricks_reload_url'] = self.get_bricks_reload_url()
        context['bricks'] = self.get_bricks()

        return context


class TitleMixin:
    """ Mixin for views with a title bar.

    Attributes:
    title : A {}-format string used by the method get_title(), which interpolates
            it with the context given by the method get_title_format_data().

    """
    title = '*insert title here*'

    def get_title(self):
        return self.title.format(**self.get_title_format_data())

    def get_title_format_data(self):
        return {}


class SubmittableMixin:
    """Mixin for views with a submission button.

    Attributes:
    submit_label: A string used as label for the submission button of the form.
                 (see get_submit_label()).
    """
    submit_label = _('Save')

    def get_submit_label(self):
        return self.submit_label


class CremeFormView(CancellableMixin,
                    PermissionsMixin,
                    TitleMixin,
                    SubmittableMixin,
                    django_generic.FormView):
    """ Base class for views with a simple form (ie: not a model form) in Creme.
    You'll have to override at least the attribute 'form_class' because the
    default one is just abstract place-holders.

    The mandatory argument "user" of forms in Creme is filled ; but no "instance"
    argument is passed to the form instance.

    It manages the common UI of Creme Forms:
      - Title of the form
      - Label for the submit button
      - Cancel button.

    Attributes:
      - atomic_POST: <True> (default value means that POST requests are
                     managed within a SQL transaction.
    """
    form_class = CremeForm
    template_name = 'creme_core/generics/blockform/add.html'
    success_url = reverse_lazy('creme_core__home')
    atomic_POST = True

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return self.handle_not_logged()

        self.check_view_permissions(user=user)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form=form)

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

    def post(self, *args, **kwargs):
        if self.atomic_POST:
            with atomic():
                return super().post(*args, **kwargs)
        else:
            return super().post(*args, **kwargs)


class CremeFormPopup(CremeFormView):
    """  Base class for view with a simple form in Creme within an Inner-Popup.
    See CremeFormView.
    """
    # template_name = 'creme_core/generics/blockform/add_popup.html'  # DO NOT USE OLD TEMPLATES !!!
    template_name = 'creme_core/generics/blockform/add-popup.html'

    def get_success_url(self):
        return ''

    def form_valid(self, form):
        form.save()
        return HttpResponse(self.get_success_url(), content_type='text/plain')


class RelatedToEntityFormPopup(EntityRelatedMixin, CremeFormPopup):
    """ This is a specialisation of CremeFormPopup made for changes
    related to a CremeEntity (eg: create several instances at once linked
    to an entity).
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
