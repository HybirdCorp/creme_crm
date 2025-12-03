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

from __future__ import annotations

import logging
from typing import Iterator

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.transaction import atomic
from django.db.utils import IntegrityError
from django.utils.translation import gettext_lazy as _

from ..global_info import get_per_request_cache
from . import fields as core_fields
from .auth import CremeUser
from .entity import CremeEntity

logger = logging.getLogger(__name__)


# TODO: move to core?
class PinnedEntities:
    """Stores the PinnedEntity instances related to a user.
    Used as a cache to perform the SQL queries only once per request.

    The size of the collection is limited (the number of instances in DB is limited).
    But if the administrator has increased the limit in the settings, then has
    decreased it, the number of instances in DB can exceed the configured limit;
    this case if managed, but il could cause extra queries to be performed.
    """
    @classmethod
    def get_for_user(cls, user: CremeUser) -> PinnedEntities:
        """Build an instance of PinnedEntities, or retrieve the instance in the cache."""
        cache = get_per_request_cache()
        key = f'creme_core-pinned-{user.id}'

        cached_instance = cache.get(key)
        if cached_instance is None:
            cached_instance = cache[key] = cls(user=user)

        return cached_instance

    def __init__(self, user: CremeUser, max_size: int | None = None):
        self._user = user
        self._max = settings.PINNED_ENTITIES_SIZE if max_size is None else max_size

        exceeded_size = self._max + 1
        content = [
            *PinnedEntity.objects.filter(user=user)
                                 .prefetch_related('real_entity')[:exceeded_size],
        ]
        if len(content) == exceeded_size:
            logger.warning(
                'The user "%s" has too much pinned entities (did you increase then '
                'decrease the value of settings.PINNED_ENTITIES_SIZE ?).',
                user.username,
            )

            content[:] = content[:self._max]
            self._exceeded = True
        else:
            self._exceeded = False

        self._content = content

    def __iter__(self) -> Iterator[PinnedEntity]:
        yield from self._content

    def is_pinned(self, entity: CremeEntity) -> bool:
        # We check the cache first to avoid query if possible...
        if any(entity.id == pinned.entity_id for pinned in self._content):
            return True

        if self._exceeded:
            # TODO: extra cache?
            return PinnedEntity.objects.filter(user=self._user, entity=entity.id).exists()

        return False

    @property
    def max_is_reached(self) -> bool:
        return len(self._content) >= self._max

    @property
    def user(self) -> CremeUser:
        return self._user


class PinnedEntityManager(models.Manager):
    # TODO: factorise (see CremePropertyManager) ?
    def safe_create(self, **kwargs) -> None:
        """Create a PinnedEntity in DB by taking care of the UNIQUE constraint.
        Notice that, unlike 'create()' it always return None (to avoid a
        query in case of IntegrityError).
        @param kwargs: same as 'create()'.
        """
        try:
            with atomic():
                self.create(**kwargs)
        except IntegrityError:
            logger.exception('Avoid a PinnedEntity duplicate: %s ?!', kwargs)

    # TODO?
    #  def safe_get_or_create(self, **kwargs) -> PinnedEntity:


class PinnedEntity(models.Model):
    """A CremeEntity can be pinned by a user.
    It's used by the menu entry "Quick access" (section "Pinned entities").
    """
    entity_ctype = core_fields.EntityCTypeForeignKey(related_name='+', editable=False)
    entity = models.ForeignKey(
        CremeEntity, related_name='+', editable=False, on_delete=models.CASCADE,
    )
    real_entity = core_fields.RealEntityForeignKey(
        ct_field='entity_ctype', fk_field='entity',
    )

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    created = core_fields.CreationDateTimeField(_('Pinned on'))

    objects = PinnedEntityManager()

    def __repr__(self):
        return f'PinnedEntity(real_entity="{self.real_entity}", user={self.user})'

    class Meta:
        app_label = 'creme_core'
        ordering = ('id',)
        unique_together = ('entity', 'user')
