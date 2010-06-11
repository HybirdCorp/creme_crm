# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from logging import debug

from creme_core.models import CremeEntity


#TODO: in settings ???
MAX_LAST_ITEMS = 9

class ItemLastViewed(object):
    def __init__ (self, entity):
        self.pk = entity.pk
        self.url = entity.get_absolute_url()
        self.update(entity)

    def __repr__ (self):
        return self.name

    def __eq__(self, other):
        return self.pk == other.pk

    def update(self, entity):
        self.name = unicode(entity)
        self.modified = entity.modified


def change_page_for_last_item_viewed(func):
    def decorator_func(request, *args, **kwargs):
        change_page_for_last_viewed(request)
        return func(request, *args, **kwargs)

    return decorator_func

def __add_item_in_last_viewed(request, item):
    debug('__add_item_in_last_viewed: %s', item)
    session = request.session
#todo , in python 2.6    
#    last_viewed_items = session.get('last_viewed_items', deque(maxlen=MAX_LAST_ITEMS))
    last_viewed_items = session.get('last_viewed_items', deque())

    try:
        last_viewed_items.remove(item)
    except ValueError:
        debug('%s not in last_viewed', item)

    last_viewed_items.appendleft(item)
    #for python 2.5
    while len(last_viewed_items) > MAX_LAST_ITEMS:
        last_viewed_items.pop()

    session['last_viewed_items'] = last_viewed_items

def change_page_for_last_viewed(request):
    current_page_viewed = request.session.pop('current_viewed_item', None)

    if current_page_viewed is not None:
        __add_item_in_last_viewed(request, current_page_viewed)

def add_item_in_last_viewed(request, entity):
    session = request.session
    current_item = session.get('current_viewed_item')

    if current_item is not None and current_item.pk == entity.pk:
        return

    item = ItemLastViewed(entity)
    __add_item_in_last_viewed(request, item)
    session['current_viewed_item'] = item

def last_viewed_items(request):
    session = request.session
    old_items = session.get('last_viewed_items')

    if not old_items:
        return ()

    date_map = dict(CremeEntity.objects.filter(pk__in=[item.pk for item in old_items]).values_list('id', 'modified'))

    items = []
    updated = False

    for item in old_items:
        date = date_map.get(int(item.pk))
        if date:
            if date > item.modified:
                updated = True
                item.update(CremeEntity.objects.get(pk=item.pk).get_real_entity())

            items.append(item)

    if updated:
        session['last_viewed_items'] = deque(items)

    return items 
