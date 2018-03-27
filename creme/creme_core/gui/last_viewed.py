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

import logging

from django.conf import settings

from ..models import CremeEntity
from creme.creme_core.utils.dates import dt_from_ISO8601, dt_to_ISO8601

logger = logging.getLogger(__name__)


class LastViewedItem(object):
    def __init__ (self, request, entity):
        self.pk = entity.pk
        self.url = entity.get_absolute_url()
        self.update(entity)

        self.__add(request)

    def __repr__ (self):
        return self.name

    def __eq__(self, other):
        return self.pk == other.pk

    def as_dict(self):
        return {'pk':       self.pk,
                'url':      self.url,
                'name':     self.name,
                'modified': dt_to_ISO8601(self.modified),
               }

    @staticmethod
    def from_dict(data):
        instance = object.__new__(LastViewedItem)

        for attr in ('pk', 'url', 'name'):
            setattr(instance, attr, data[attr])

        instance.modified = dt_from_ISO8601(data['modified'])

        return instance

    def update(self, entity):
        self.name = unicode(entity)
        self.modified = entity.modified

    def __add(self, request):
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

    @staticmethod
    def _deserialize_all(session):
        from_dict = LastViewedItem.from_dict
        return [from_dict(data) for data in session.get('last_viewed_items', ())]

    @staticmethod
    def _serialize_all(session, items):
        session['last_viewed_items'] = [item.as_dict() for item in items]

    # TODO: use the future entity representation table
    @staticmethod
    def get_all(request):
        items = []
        session = request.session
        old_items = LastViewedItem._deserialize_all(session)

        if old_items:
            MAX_LAST_ITEMS = settings.MAX_LAST_ITEMS
            updated = False

            if len(old_items) > MAX_LAST_ITEMS:
                updated = True  # The settings has change since the list has been stored
                del old_items[MAX_LAST_ITEMS:]

            # entities = {e.id: e for e in CremeEntity.objects
            #                                         .filter(is_deleted=False,
            #                                                 pk__in=[item.pk for item in old_items],
            #                                                )
            #            }
            entities = CremeEntity.objects.filter(is_deleted=False) \
                                          .in_bulk([item.pk for item in old_items])
            updated |= (len(old_items) != len(entities))  # If any entity has been deleted -> must update

            for item in old_items:
                entity = entities.get(item.pk)

                if entity:
                    if entity.modified > item.modified:
                        updated = True
                        item.update(entity.get_real_entity())  # TODO: use CremeEntity.populate_real_entities()

                    items.append(item)

            if updated:
                LastViewedItem._serialize_all(session, items)

        return items
