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

from logging import debug

from django.db.models import Model, CharField, ForeignKey, BooleanField, PositiveIntegerField, PositiveSmallIntegerField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from relation import RelationType
from entity import CremeEntity


HFI_ACTIONS  = 0
HFI_FIELD    = 1
HFI_RELATION = 2
HFI_FUNCTION = 3
HFI_CUSTOM   = 4


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
        from collections import defaultdict

        hfi_groups = defaultdict(list) #useless if only relations optim.... wait & see

        for hfi in self.items:
            hfi_groups[hfi.type].append(hfi)

        #print 'CUSTOMS GROUP',   hfi_groups[HFI_CUSTOM]

        relations_hfi = hfi_groups[HFI_RELATION]
        if relations_hfi:
            CremeEntity.populate_relations(entities, [hfi.relation_predicat_id for hfi in relations_hfi])


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

    def __unicode__(self):
        return u"<HeaderFilterItem: order: %i, name: %s, title: %s>" % (self.order, self.name, self.title)

    class Meta:
        app_label = 'creme_core'


_hfi_action = HeaderFilterItem(order=0, name='entity_actions', title='Actions', type=HFI_ACTIONS, has_a_filter=False, editable=False, is_hidden=False)
