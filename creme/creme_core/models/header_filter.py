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

import logging

from django.db.models import Model, CharField, ForeignKey, BooleanField, PositiveIntegerField, PositiveSmallIntegerField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from relation import RelationType


HFI_FIELD    = 1
HFI_RELATION = 2
HFI_FUNCTION = 3


class HeaderFilter(Model): #CremeModel ???
    id          = CharField(primary_key=True, max_length=100)
    name        = CharField(max_length=100, verbose_name=_('Nom de la vue'))
    entity_type = ForeignKey(ContentType, editable=False)
    is_custom   = BooleanField(blank=False, default=True)

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return u'<HeaderFilter: name="%s">' % self.name


class HeaderFilterItem(Model):  #CremeModel ???
    id                    = CharField(primary_key=True, max_length=100)
    order                 = PositiveIntegerField()
    name                  = CharField(max_length=100)
    title                 = CharField(max_length=100)
    type                  = PositiveSmallIntegerField() #see HFI_FIELD, HFI_RELATION, HFI_FUNCTION
    header_filter         = ForeignKey(HeaderFilter)
    has_a_filter          = BooleanField(blank=True, default=False)
    editable              = BooleanField(blank=True, default=True)
    sortable              = BooleanField(blank=True, default=False)
    is_hidden             = BooleanField(blank=True, default=False)
    filter_string         = CharField(max_length=100, blank=True, null=True)
    relation_predicat     = ForeignKey(RelationType, blank=True, null=True) #rename ???
    relation_content_type = ForeignKey(ContentType, blank=True, null=True)

    def __unicode__(self):
        return u" Order : %i , name : %s , Title : %s   " % (self.order, self.name, self.title)

    class Meta:
        app_label = 'creme_core'
