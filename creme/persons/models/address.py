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

from django.db.models import Model, CharField, TextField, ForeignKey, PositiveIntegerField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _, ugettext
from django import forms
from django.forms import ModelForm

from creme_core.models import CremeEntity, CremeModel


class Address(CremeModel):
    name    = CharField(_(u"Name"), max_length=100, blank=True, null=True)
    address = TextField(_(u"Address"), blank=True, null=True)
    po_box  = CharField(_(u"PO box"), max_length=50, blank=True, null=True)
    city    = CharField(_(u"City"), max_length=100, blank=True, null=True)
    state   = CharField(_(u"State"), max_length=100, blank=True, null=True)
    zipcode = CharField(_(u"Zip code"), max_length=100, blank=True, null=True)
    country = CharField(_(u"Country"), max_length=40, blank=True, null=True)

    content_type = ForeignKey(ContentType, related_name="object_set")
    object_id    = PositiveIntegerField()
    owner        = GenericForeignKey(ct_field="content_type", fk_field="object_id")

    research_fields = CremeEntity.research_fields + ['address', 'po_box', 'city', 'state', 'zipcode', 'country']

    class Meta:
        app_label = 'persons'
        verbose_name = _(u'Address')
        verbose_name_plural = _(u'Addresses')

    def __str__(self): #useful ????
        return '%s %s %s' % (self.address, self.zipcode, self.city)

    def __unicode__(self):
        return force_unicode('%s %s %s' % (self.address, self.zipcode, self.city))

    @staticmethod
    def inject_fields(form, suffix=""):
        if not isinstance(form, ModelForm):
            raise Exception("This is not a form.ModelForm instance")

        #TODO: use a true form to generate automatically fields ????
        fields = form.fields
        CharField = forms.CharField
        _ = ugettext
        fields['name' + suffix]    = CharField(label=_(u"Address name"), max_length=100, required=False)
        fields['address' + suffix] = CharField(label=_(u"Address"), max_length=100, widget=forms.Textarea, required=False)
        fields['po_box' + suffix]  = CharField(label=_(u"PO box"), max_length=50, required=False)
        fields['city' + suffix]    = CharField(label=_(u"City"), max_length=100, required=False)
        fields['state' + suffix]   = CharField(label=_(u"State"), max_length=100, required=False)
        fields['zipcode' + suffix] = CharField(label=_(u"Zip code"), max_length=20, required=False)
        fields['country' + suffix] = CharField(label=_(u"Country"), max_length=40, required=False)
