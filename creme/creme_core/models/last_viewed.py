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
from django.contrib.auth import get_user_model
from django.db import connection, models
from django.db.models import F
from django.db.transaction import atomic
from django.utils.timezone import now

from . import fields as core_fields
from .entity import CremeEntity


class LastViewedEntityManager(models.Manager):
    @atomic
    def create(self, *, user, real_entity):  # **kwargs ??
        """Returns an instance of LastViewedEntity
        It could create a new instance, but it tries to recycle the limited
        number of instance (see settings.LAST_ENTITIES_SIZE).
        """
        # NB: on PG we do not lock CremeEntity because it's not possible with
        #     the nullable relation.
        sfu_kwargs = {'of': ('self',)} if connection.vendor == 'postgresql' else {}
        items = [
            *self.filter(user=user)
                 .annotate(entity_is_deleted=F('entity__is_deleted'))
                 .select_for_update(**sfu_kwargs)
        ]
        # NB: is >=1 (see <creme_core.checks.check_last_entities()>)
        LAST_ENTITIES_SIZE = settings.LAST_ENTITIES_SIZE

        length = len(items)
        if length > LAST_ENTITIES_SIZE:
            # It seems LAST_ENTITIES_SIZE is smaller since the last run
            self.filter(id__in=[item.id for item in items[LAST_ENTITIES_SIZE:]]).delete()
            items = items[:settings.LAST_ENTITIES_SIZE]

        # We just update the item if it's already present
        for item in items:
            if item.entity_id == real_entity.id:
                item.viewed = now()
                item.save()

                return item

        # We try to recycle 'empty' slot (the related entity has been deleted)
        for item in items:
            if item.entity_id is None:
                item.real_entity = real_entity
                item.save()

                return item

        # We try to recycle slot related to an entity marked as deleted
        for item in items:
            # NB: see annotate() above (we avoid a query or a .select_related())
            if item.entity_is_deleted:
                item.real_entity = real_entity
                item.save()

                return item

        if length < LAST_ENTITIES_SIZE:
            item = super().create(user=user, real_entity=real_entity)
        else:
            item = items[-1]
            item.real_entity = real_entity
            item.save()

        return item


class LastViewedEntity(models.Model):
    """Store the more recent entities a user has viewed (i.e. the user went
    to their detail-view).
    It's used by the menu entry "Quick access" (section "Recent entities").
    """
    entity_ctype = core_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity = models.ForeignKey(
        CremeEntity,
        related_name='+', editable=False,
        # NB: when the related entity is deleted, we keep we slot to avoid
        # creating a new instance & so we recycle IDs
        # (see <LastViewedEntityManager.create()>).
        on_delete=models.SET_NULL, null=True,
    )
    real_entity = core_fields.RealEntityForeignKey(
        ct_field='entity_ctype', fk_field='entity',
    )

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    viewed = core_fields.ModificationDateTimeField()

    objects = LastViewedEntityManager()

    def __repr__(self):
        return f'LastViewedEntity(real_entity="{self.real_entity}", user={self.user})'

    class Meta:
        app_label = 'creme_core'
        ordering = ('-viewed',)
        # Not unique_together = ('entity', 'user') because of entity=NULL
