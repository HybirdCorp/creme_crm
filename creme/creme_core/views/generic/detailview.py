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

import logging
from collections import defaultdict
from itertools import chain

from django.db.models import Q
from django.urls import reverse
from django.views.generic import DetailView

from creme.creme_core.core import imprint
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.gui.last_viewed import LastViewedItem
from creme.creme_core.models import (
    BrickDetailviewLocation,
    CremeEntity,
    CremeModel,
)

from . import base

logger = logging.getLogger(__name__)


def detailview_bricks(user, entity, registry=brick_registry):
    is_superuser = user.is_superuser
    role = user.role

    role_q = Q(role=None, superuser=True) if is_superuser else Q(role=role, superuser=False)
    locs = BrickDetailviewLocation.objects.filter(
        Q(content_type=None) | Q(content_type=entity.entity_type)
    ).filter(
        role_q | Q(role=None, superuser=False)
    ).order_by('order')

    # We fallback to the default config is there is no config for this content type.
    locs = [
        loc
        for loc in locs
        # NB: useless as long as default conf cannot have a related role
        if loc.superuser == is_superuser and loc.role == role
    ] or [
        loc for loc in locs if loc.content_type_id is not None
    ] or locs
    loc_map = defaultdict(list)

    for loc in locs:
        brick_id = loc.brick_id

        if brick_id:  # Populate scripts can leave void brick ids
            loc_map[loc.zone].append(brick_id)

    # We call the method block_registry.get_bricks() once to regroup additional queries
    bricks = {}
    model = entity.__class__
    for brick in registry.get_bricks(
        [*chain.from_iterable(brick_ids for brick_ids in loc_map.values())],
        entity=entity,
    ):
        target_ctypes = brick.target_ctypes
        if target_ctypes and model not in target_ctypes:
            logger.warning(
                'This brick cannot be displayed on this content type '
                '(you have a config problem): %s',
                brick.id_,
            )
        else:
            bricks[brick.id_] = brick

    hat_bricks = loc_map[BrickDetailviewLocation.HAT]
    if not hat_bricks:
        hat_brick = registry.get_generic_hat_brick(model)

        hat_bricks.append(hat_brick.id_)
        bricks[hat_brick.id_] = hat_brick

    return {
        zone_name: [
            *filter(None, (bricks.get(brick_id) for brick_id in loc_map[zone])),
        ]
        for zone, zone_name in BrickDetailviewLocation.ZONE_NAMES.items()
    }


class CremeModelDetail(base.PermissionsMixin, base.BricksMixin, DetailView):
    """ Base class for detail view in Creme.
    You'll have to override at least the attribute 'model.
    """
    model = CremeModel
    template_name = 'creme_core/detailview.html'
    pk_url_kwarg = 'object_id'
    bricks_reload_url_name = ''

    def check_instance_permissions(self, instance, user):
        pass

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return self.handle_not_logged()

        self.check_view_permissions(user=user)

        return super().dispatch(request, *args, **kwargs)

    def get_bricks_reload_url(self):
        name = self.bricks_reload_url_name
        return reverse(name, args=(self.object.id,)) if name else ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bricks'] = self.get_bricks()
        context['bricks_reload_url'] = self.get_bricks_reload_url()

        return context

    def get_object(self, queryset=None):
        instance = super().get_object(queryset=queryset)
        self.check_instance_permissions(instance=instance, user=self.request.user)

        return instance


class RelatedToEntityDetail(CremeModelDetail):
    """ This specialisation of CremeModelDetail is made for models
    related to a CremeEntity instance.
    """
    def check_instance_permissions(self, instance, user):
        user.has_perm_to_view_or_die(instance.get_related_entity())


class EntityDetail(CremeModelDetail):
    """ Base class for detail view of CremeEntities.

    It manages :
      - The permission checking.
      - The correct template context to have the Bricks corresponding to the model.
      - The Insertion of the entity in the last-viewed items.
      - The creation of an Imprint instance (if needed).
    """
    model = CremeEntity
    template_name = 'creme_core/generics/view_entity.html'
    pk_url_kwarg = 'entity_id'
    bricks_reload_url_name = 'creme_core__reload_detailview_bricks'

    imprint_manager = imprint.imprint_manager

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_view_or_die(instance)

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_access_or_die(self.model._meta.app_label)

    def get_bricks(self):
        return detailview_bricks(
            self.request.user, self.object, registry=self.brick_registry,
        )

    def get_object(self, *args, **kwargs):
        entity = super().get_object(*args, **kwargs)
        request = self.request

        LastViewedItem(request, entity)
        self.imprint_manager.create_imprint(entity=entity, user=request.user)

        return entity


class CremeModelDetailPopup(base.TitleMixin, CremeModelDetail):
    """ Base class for inner-popup displaying the detailed information
    of an instance.
    """
    template_name = 'creme_core/generics/detail-popup.html'
    title = '{object}'
    bricks_reload_url_name = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.get_title()

        return context

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['object'] = self.object

        return data


class EntityDetailPopup(CremeModelDetailPopup):
    bricks_reload_url_name = 'creme_core__reload_detailview_bricks'

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_view_or_die(instance)

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_access_or_die(self.model._meta.app_label)


class RelatedToEntityDetailPopup(CremeModelDetailPopup):
    """ This specialisation of CremeModelDetailPopup is made for models
    related to a CremeEntity instance.
    """
    def check_instance_permissions(self, instance, user):
        user.has_perm_to_view_or_die(instance.get_related_entity())

    # TODO ?
    # def get_title_format_data(self):
    #     data = super().get_title_format_data()
    #     data['entity'] = self.object.get_related_entity().allowed_str(self.request.user)
    #
    #     return data
