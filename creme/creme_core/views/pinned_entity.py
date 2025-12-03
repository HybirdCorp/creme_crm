################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import ngettext

from ..core.exceptions import ConflictError
from ..models import PinnedEntity
from . import generic


class EntityPinning(generic.base.EntityRelatedMixin, generic.CheckedView):
    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)

    def post(self, request, *args, **kwargs):
        user = request.user
        size = settings.PINNED_ENTITIES_SIZE
        if PinnedEntity.objects.filter(user=user).count() >= size:
            raise ConflictError(
                ngettext(
                    'You cannot have more than {count} pinned entity',
                    'You cannot have more than {count} pinned entities',
                    size,
                ).format(count=size)
            )

        entity = self.get_related_entity()
        PinnedEntity.objects.safe_create(user=user, real_entity=entity)

        return HttpResponse()


class EntityUnPinning(generic.CheckedView):
    entity_id_url_kwarg = 'entity_id'

    def post(self, request, *args, **kwargs):
        PinnedEntity.objects.filter(
            entity=self.kwargs[self.entity_id_url_kwarg], user=request.user,
        ).delete()

        return HttpResponse()
