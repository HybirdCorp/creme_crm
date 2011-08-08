# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.db.models import Model, CharField, TextField, ForeignKey, PositiveIntegerField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
#from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django import forms
from django.forms import ModelForm

from creme_core.models import CremeEntity, CremeModel


class Address(CremeModel):
    name       = CharField(_(u"Name"), max_length=100, blank=True, null=True)
    address    = TextField(_(u"Address"), blank=True, null=True)
    po_box     = CharField(_(u"PO box"), max_length=50, blank=True, null=True)
    zipcode    = CharField(_(u"Zip code"), max_length=100, blank=True, null=True)
    city       = CharField(_(u"City"), max_length=100, blank=True, null=True)
    department = CharField(_(u"Department"), max_length=100, blank=True, null=True)
    state      = CharField(_(u"State"), max_length=100, blank=True, null=True)
    country    = CharField(_(u"Country"), max_length=40, blank=True, null=True)

    content_type = ForeignKey(ContentType, related_name="object_set")
    object_id    = PositiveIntegerField()
    owner        = GenericForeignKey(ct_field="content_type", fk_field="object_id")

    research_fields = CremeEntity.research_fields + ['address', 'po_box', 'zipcode', 'city', 'department', 'state', 'country']
    header_filter_exclude_fields = CremeEntity.header_filter_exclude_fields + ['object_id', ]

    class Meta:
        app_label = 'persons'
        verbose_name = _(u'Address')
        verbose_name_plural = _(u'Addresses')

    #COMMENTED on 21 march 2011
    #def __str__(self):
        #return '%s %s %s %s' % (self.address, self.zipcode, self.city, self.department)

    def __unicode__(self):
        #return force_unicode('%s %s %s %s' % (self.address, self.zipcode, self.city, self.department)) #COMMENTED on 21 march 2011
        return u'%s %s %s %s' % (self.address, self.zipcode, self.city, self.department)

    def get_related_entity(self): #for generic views
        return self.owner

    _INFO_FIELD_NAMES = ('name', 'address', 'po_box', 'zipcode', 'city', 'department', 'state', 'country')

    #TODO: unitest ??
    def __nonzero__(self): #used by forms to detect empty addresses
        return any(getattr(self, fname) for fname in self._INFO_FIELD_NAMES)

    def clone(self, entity):
        """Returns a new cloned (saved) address for a (saved) entity"""
        return Address.objects.create(name=self.name, address=self.address, po_box=self.po_box,
                                      city=self.city, state=self.state, zipcode=self.zipcode,
                                      country=self.country, department=self.department,
                                      content_type=ContentType.objects.get_for_model(entity), object_id=entity.id)
