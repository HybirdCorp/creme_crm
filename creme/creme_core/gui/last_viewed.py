# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from collections import deque
import logging

from ..models import CremeEntity


logger = logging.getLogger(__name__)
MAX_LAST_ITEMS = 9 #TODO: in settings ???


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

    def update(self, entity):
        self.name = unicode(entity)
        self.modified = entity.modified

    def __add(self, request):
        logger.debug('LastViewedItem.add: %s', self)
        session = request.session
        last_viewed_items = session.get('last_viewed_items', deque(maxlen=MAX_LAST_ITEMS))
        #last_viewed_items = session.get('last_viewed_items', deque())

        if last_viewed_items and last_viewed_items[0] == self:
            return

        try:
            last_viewed_items.remove(self)
        except ValueError:
            logger.debug('%s not in last_viewed', self)

        last_viewed_items.appendleft(self)
        #while len(last_viewed_items) > MAX_LAST_ITEMS:
            #last_viewed_items.pop()

        session['last_viewed_items'] = last_viewed_items

    #TODO: use the future entity representation table
    @staticmethod
    def get_all(request):
        session = request.session
        old_items = session.get('last_viewed_items')

        if not old_items:
            return ()

        entities = dict((e.id, e) for e in CremeEntity.objects.filter(is_deleted=False, 
                                                                      pk__in=[item.pk for item in old_items],
                                                                     )
                       )
        items = []
        updated = (len(old_items) != len(entities)) #if any entitiy has been deleted -> must update

        for item in old_items:
            entity = entities.get(item.pk)

            if entity:
                if entity.modified > item.modified:
                    updated = True
                    item.update(entity.get_real_entity()) #TODO: use CremeEntity.populate_real_entities()

                items.append(item)

        if updated:
            session['last_viewed_items'] = deque(items)

        return items
