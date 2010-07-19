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

from collections import defaultdict
from logging import debug

from django.db.models import Model, CharField, ForeignKey, BooleanField, PositiveIntegerField, PositiveSmallIntegerField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from relation import RelationType
from entity import CremeEntity
from custom_field import CustomField


HFI_ACTIONS  = 0
HFI_FIELD    = 1
HFI_RELATION = 2
HFI_FUNCTION = 3
HFI_CUSTOM   = 4


class HeaderFilterList(list):
    """Contains all the HeaderFilter objects corresponding to a CremeEntity's ContentType.
    Indeed, it's as a cache.
    """
    def __init__(self, content_type):
        super(HeaderFilterList, self).__init__(HeaderFilter.objects.filter(entity_type=content_type).order_by('name'))
        self._selected = None

    @property
    def selected(self):
        return self._selected

    def select_by_id(self, *ids):
        """Try several HeaderFilter ids"""
        #linear search but with few items after all....
        for hf_id in ids:
            for hf in self:
                if hf.id == hf_id:
                    self._selected = hf
                    return hf

        if self:
            self._selected = self[0]
        else:
            self._selected = None

        return self._selected


class HeaderFilter(Model): #CremeModel ???
    id          = CharField(primary_key=True, max_length=100)
    name        = CharField(max_length=100, verbose_name=_('Nom de la vue'))
    entity_type = ForeignKey(ContentType, editable=False)
    is_custom   = BooleanField(blank=False, default=True)

    _items = None

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return u'<HeaderFilter: name="%s">' % self.name

    def build_items(self, show_actions=False):
        items = self.header_filter_items.order_by('order')

        if show_actions:
            items = list(items)
            items.insert(0, _hfi_action)

        self._items = items

    @property
    def items(self):
        if self._items is None:
            self.build_items()
        return self._items

    #TODO: select_related() for fk attr ??
    def populate_entities(self, entities):
        hfi_groups = defaultdict(list) #useless if only relations optim.... wait & see

        for hfi in self.items:
            hfi_groups[hfi.type].append(hfi)

        group = hfi_groups[HFI_RELATION]
        if group:
            CremeEntity.populate_relations(entities, [hfi.relation_predicat_id for hfi in group])

        group = hfi_groups[HFI_CUSTOM]
        if group:
            cfields = CustomField.objects.in_bulk([int(hfi.name) for hfi in group])

            for hfi in group:
                hfi._customfield = cfields[int(hfi.name)]

            CremeEntity.populate_custom_values(entities, cfields.values()) #NB: not itervalues() (iterated several times)


class HeaderFilterItem(Model):  #CremeModel ???
    id                    = CharField(primary_key=True, max_length=100)
    order                 = PositiveIntegerField()
    name                  = CharField(max_length=100)
    title                 = CharField(max_length=100)
    type                  = PositiveSmallIntegerField() #==> {HFI_FIELD, HFI_RELATION, HFI_FUNCTION, HFI_CUSTOM}
    header_filter         = ForeignKey(HeaderFilter, related_name='header_filter_items')
    has_a_filter          = BooleanField(blank=True, default=False)  #TODO: useful ?? retrievable with type ??
    editable              = BooleanField(blank=True, default=True)   #TODO: useful ?? retrievable with type ??
    sortable              = BooleanField(blank=True, default=False)  #TODO: useful ?? retrievable with type ??
    is_hidden             = BooleanField(blank=True, default=False)  #TODO: useful ?? retrievable with type ??
    filter_string         = CharField(max_length=100, blank=True, null=True)
    relation_predicat     = ForeignKey(RelationType, blank=True, null=True) #TODO: rename to 'relation_type' ???  use 'name' to store pk instead ????
    relation_content_type = ForeignKey(ContentType, blank=True, null=True) #TODO: useful ??

    def __init__(self, *args, **kwargs):
        super(HeaderFilterItem, self).__init__(*args, **kwargs)
        self._customfield = None

    def __unicode__(self):
        return u"<HeaderFilterItem: order: %i, name: %s, title: %s>" % (self.order, self.name, self.title)

    class Meta:
        app_label = 'creme_core'

    def get_customfield(self):
        assert self.type == HFI_CUSTOM

        if self._customfield is None:
            debug('HeaderFilterItem.get_customfield(): cache MISS for id=%s', self.id)
            self._customfield = CustomField.objects.get(pk=self.name)
        else:
            debug('HeaderFilterItem.get_customfield(): cache HIT for id=%s', self.id)

        return self._customfield


_hfi_action = HeaderFilterItem(order=0, name='entity_actions', title='Actions', type=HFI_ACTIONS, has_a_filter=False, editable=False, is_hidden=False)
