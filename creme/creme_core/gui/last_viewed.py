# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
from typing import List

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from ..models import CremeEntity
from ..utils.dates import dt_from_ISO8601, dt_to_ISO8601

logger = logging.getLogger(__name__)


class LastViewedItem:
    def __init__(self, request, entity: CremeEntity):
        self.pk = entity.pk
        self.ctype_id = entity.entity_type_id
        self.url = entity.get_absolute_url()
        self.update(entity)

        self.__add(request)

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return self.pk == other.pk

    def as_dict(self) -> dict:
        return {
            'pk':       self.pk,
            'ctype_id': self.ctype_id,
            'url':      self.url,
            'name':     self.name,
            'modified': dt_to_ISO8601(self.modified),
        }

    @property
    def ctype(self):
        ct_id = self.ctype_id
        return None if ct_id is None else ContentType.objects.get_for_id(ct_id)

    @classmethod
    def from_dict(cls, data: dict):
        instance = object.__new__(cls)

        for attr in ('pk', 'url', 'name'):
            setattr(instance, attr, data[attr])

        # TODO: make mandatory once we're sure a Session flush has been made (creme 2.4?)
        #       + rework @ctype
        #       + rework creme.creme_core.menu.RecentEntitiesEntry
        instance.ctype_id = data.get('ctype_id')

        instance.modified = dt_from_ISO8601(data['modified'])

        return instance

    def update(self, entity: CremeEntity) -> None:
        self.name = str(entity)
        self.modified = entity.modified

    def __add(self, request) -> None:
        logger.debug('LastViewedItem.add: %s', self)
        session = request.session
        last_viewed_items = self._deserialize_all(session)

        if last_viewed_items and last_viewed_items[0] == self:
            return

        try:
            last_viewed_items.remove(self)
        except ValueError:
            logger.debug('%s not in last_viewed', self)

        last_viewed_items.insert(0, self)
        del last_viewed_items[settings.MAX_LAST_ITEMS:]

        self._serialize_all(session, last_viewed_items)

    @classmethod
    def _deserialize_all(cls, session) -> List['LastViewedItem']:
        from_dict = cls.from_dict
        return [from_dict(data) for data in session.get('last_viewed_items', ())]

    @staticmethod
    def _serialize_all(session, items) -> None:
        session['last_viewed_items'] = [item.as_dict() for item in items]

    # TODO: use the future entity representation table
    @classmethod
    def get_all(cls, request) -> List['LastViewedItem']:
        items = []
        session = request.session
        old_items = cls._deserialize_all(session)

        if old_items:
            MAX_LAST_ITEMS = settings.MAX_LAST_ITEMS
            updated = False

            if len(old_items) > MAX_LAST_ITEMS:
                # The 'settings' value has changed since the list has been stored
                updated = True

                del old_items[MAX_LAST_ITEMS:]

            entities = CremeEntity.objects.filter(
                is_deleted=False,
            ).in_bulk([item.pk for item in old_items])
            # If any entity has been deleted -> must update
            updated |= (len(old_items) != len(entities))

            for item in old_items:
                entity = entities.get(item.pk)

                if entity:
                    if entity.modified > item.modified:
                        updated = True
                        # TODO: use CremeEntity.populate_real_entities() or ctype_id
                        item.update(entity.get_real_entity())

                    items.append(item)

            if updated:
                cls._serialize_all(session, items)

        return items
