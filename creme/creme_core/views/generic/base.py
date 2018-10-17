# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.core.exceptions import ConflictError
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


class PermissionsMixin:
    """Mixin that helps checking the global permission of a view.
    The needed permissions are stored in the attribute <permissions>, an could be:
      - a string. Eg:
          permissions = 'my_app'
      - a sequence of strings. Eg:
          permissions = ['my_app1', 'my_app2.can_admin']
      - <None> (default value) means no permission is checked.
    """
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
                raise PermissionDenied(_('You are not allowed to access this view.'))


class EntityRelatedMixin:
    """Mixin which help building view which retrieve a CremeEntity instance,
    in order to add it some additional data (generally stored in an object
    referencing this entity).

    Attributes:
    entity_id_url_kwarg: string indicating the name of the key-word (ie <self.kwargs>)
                         which stores the ID oh the related entity.
    entity_classes: it can be:
        - None => that all model of CremeEntity are accepted ; a second query
         is done to retrieve the real entity.
        - a class (inheriting <CremeEntity>) => only entities of this class are
          retrieved (& 1 query is done, not 2, to retrieve it).
        - a sequence (list/tuple) of classes (inheriting <CremeEntity>) => only
          entities of one of these classes are accepted ; a second query is done
          to retrieve the real entity if the class is accepted.

    Tips: override <check_related_entity_permissions()> if you want to check
    LINK permission instead of CHANGE.
    """
    entity_id_url_kwarg = 'entity_id'
    entity_classes = None

    def check_related_entity_permissions(self, entity, user):
        """ Check the permissions of the related entity which just has been retrieved.

        @param entity: Instance of model inheriting CremeEntity.
        @param user: Instance of <auth.get_user_model()>.
        @raise: PermissionDenied.
        """
        user.has_perm_to_change_or_die(entity)

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

    def get_ctype(self):
        try:
            ctype = getattr(self, 'related_ctype')
        except AttributeError:
            ct_id = self.kwargs[self.ctype_id_url_kwarg]

            if self.ct_id_0_accepted and not int(ct_id):
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


class CheckedTemplateView(PermissionsMixin, TemplateView):
    """Creme version of the django's TemplateView ; it checked that the
    user is logged & has some permission.
    """
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.check_view_permissions(user=self.request.user)

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
        return reverse(self.bricks_reload_url_name)


class BricksView(BricksMixin, CheckedTemplateView):
    """Base view which uses Bricks for its display."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bricks_reload_url'] = self.get_bricks_reload_url()
        context['bricks'] = self.get_bricks()

        return context
