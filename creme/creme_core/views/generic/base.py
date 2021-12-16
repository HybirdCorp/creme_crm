# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2021  Hybird
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
from typing import Iterable, List, Optional, Sequence, Type, Union
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.db.models.query import QuerySet
from django.db.transaction import atomic
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views import generic as django_generic

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import CremeForm
from creme.creme_core.gui.bricks import Brick, brick_registry
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.creme_core.models import CremeEntity, CustomFormConfigItem
from creme.creme_core.utils.content_type import get_ctype_or_404

from ..utils import build_cancel_path

logger = logging.getLogger(__name__)


class CancellableMixin:
    """Mixin that helps building an URL to go back when the user is in a form."""
    cancel_url_post_argument = 'cancel_url'

    # NB: for linters only
    request: HttpRequest

    def get_cancel_url(self) -> Optional[str]:
        request = self.request

        return (
            request.POST.get(self.cancel_url_post_argument)
            if request.method == 'POST' else
            build_cancel_path(request)
        )


class CallbackMixin:
    """Mixin which helps to retrieve an (internal) redirection-URL
    (from the GET request) in a form view.
    """
    callback_url_argument = 'callback_url'

    # NB: for linters only
    request: HttpRequest

    def get_callback_url(self) -> Optional[str]:
        request = self.request

        if request.method == 'POST':
            return request.POST.get(self.callback_url_argument)

        url = request.GET.get(self.callback_url_argument, '')

        if url:
            # NB: only internal URLs are accepted
            if not url.startswith('/') or url.startswith('//'):
                logger.warning(
                    'CallbackMixin.get_callback_url(): suspicious URL: %s',
                    url,
                )
            else:
                return url

        return None


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
      - an empty value (like '', the default value) means no permission is checked.
    """
    login_url_name: Optional[str] = None
    login_redirect_arg_name: str = REDIRECT_FIELD_NAME
    # permissions: Union[str, Sequence[str], None] = None
    permissions: Union[str, Sequence[str]] = ''

    # NB: for linters only
    request: HttpRequest

    def check_view_permissions(self, user):
        """Check global permission of the view.

        @param user: Instance of <auth.get_user_model()>.
        @raise: PermissionDenied.
        """
        permissions = self.permissions

        # if permissions is not None:
        if permissions:
            # TODO: has_perm[s]_or_die() with better error message ?
            allowed = (
                user.has_perm(permissions)
                if isinstance(permissions, str) else
                user.has_perms(permissions)
            )

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
    entity_id_url_kwarg: str = 'entity_id'
    entity_classes: Union[Type[CremeEntity], Sequence[Type[CremeEntity]], None] = None
    entity_form_kwarg: Optional[str] = 'entity'
    entity_select_for_update: bool = False

    # NB: for linters only
    request: HttpRequest
    kwargs: dict

    def build_related_entity_queryset(self, model: Type[CremeEntity]) -> QuerySet:
        qs = model._default_manager.all()
        return qs if not self.get_entity_select_for_update() else qs.select_for_update()

    def check_related_entity_permissions(self, entity: CremeEntity, user) -> None:
        """ Check the permissions of the related entity which just has been retrieved.

        @param entity: Instance of model inheriting CremeEntity.
        @param user: Instance of <auth.get_user_model()>.
        @raise: PermissionDenied.
        """
        user.has_perm_to_change_or_die(entity)

    def check_entity_classes_apps(self, user) -> None:
        entity_classes = self.entity_classes

        if entity_classes is not None:
            has_perm = user.has_perm_to_access_or_die

            if isinstance(entity_classes, type):  # CremeEntity sub-model
                # assert issubclass(entity_classes, CremeEntity)
                has_perm(entity_classes._meta.app_label)
            else:  # Sequence of classes
                for app_label in {c._meta.app_label for c in entity_classes}:
                    has_perm(app_label)

    def get_related_entity_id(self) -> str:
        return self.kwargs[self.entity_id_url_kwarg]

    def get_related_entity(self) -> CremeEntity:
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
                entity = get_object_or_404(
                    self.build_related_entity_queryset(CremeEntity),
                    id=entity_id,
                ).get_real_entity()
            elif isinstance(entity_classes, (list, tuple)):  # Sequence of classes
                get_for_ct = ContentType.objects.get_for_model
                entity = get_object_or_404(
                    self.build_related_entity_queryset(CremeEntity),
                    id=entity_id,
                    entity_type__in=[get_for_ct(c) for c in entity_classes],
                ).get_real_entity()
            else:
                assert isinstance(entity_classes, type)
                assert issubclass(entity_classes, CremeEntity)
                entity = get_object_or_404(
                    self.build_related_entity_queryset(entity_classes),
                    id=entity_id,
                )

            self.check_related_entity_permissions(entity=entity, user=self.request.user)

            self.related_entity = entity

        return entity

    def get_entity_select_for_update(self) -> bool:
        return self.entity_select_for_update

    def set_entity_in_form_kwargs(self, form_kwargs) -> None:
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
    ctype_id_url_kwarg: str = 'ct_id'
    ct_id_0_accepted: bool = False

    # NB: for linters only
    kwargs: dict
    related_ctype: ContentType

    def check_related_ctype(self, ctype: ContentType) -> None:
        pass

    def get_ctype_id(self) -> str:
        return self.kwargs[self.ctype_id_url_kwarg]

    def get_ctype(self) -> ContentType:
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
                ctype = get_ctype_or_404(ct_id)

                self.check_related_ctype(ctype)

            self.related_ctype = ctype

        return ctype


class EntityCTypeRelatedMixin(ContentTypeRelatedMixin):
    """Specialisation of ContentTypeRelatedMixin to retrieve a ContentType
    related to a CremeEntity child class.
    """
    # NB: for linters only
    request: HttpRequest

    def check_related_ctype(self, ctype):
        self.request.user.has_perm_to_access_or_die(ctype.app_label)

        model = ctype.model_class()
        if not issubclass(model, CremeEntity):
            raise ConflictError(f'This model is not a entity model: {model}')


class CustomFormMixin:
    """Mixin for form-views which want to retrieve their form class as a
    classical class, or from a CustomFormDescriptor.
    """
    # @staticmethod
    # def get_custom_form_class(form_class):
    def get_custom_form_class(self, form_class):
        if isinstance(form_class, CustomFormDescriptor):
            # TODO: raise 404 if invalid item ID ????
            # return form_class.build_form_class()
            try:
                return form_class.build_form_class(
                    item=CustomFormConfigItem.objects.get_for_user(
                        descriptor=form_class, user=self.request.user,
                    ),
                )
            except CustomFormConfigItem.DoesNotExist as e:
                raise Http404(
                    gettext(
                        'No default form has been created in DataBase for the '
                        'model «{model}». Contact your administrator.'
                    ).format(model=form_class.model._meta.verbose_name)
                ) from e

        return form_class


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
    bricks_reload_url_name: str = 'creme_core__reload_bricks'

    def get_brick_ids(self) -> Iterable[str]:
        return ()

    def get_bricks(self) -> List[Brick]:
        return [*self.brick_registry.get_bricks(
            [id_ for id_ in self.get_brick_ids() if id_]
        )]

    def get_bricks_reload_url(self) -> str:
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
    title: str = '*insert title here*'

    def get_title(self) -> str:
        return self.title.format(**self.get_title_format_data())

    def get_title_format_data(self) -> dict:
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
    form_class: Type[CremeForm] = CremeForm
    template_name = 'creme_core/generics/blockform/add.html'
    success_url = reverse_lazy('creme_core__home')
    atomic_POST: bool = True

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
