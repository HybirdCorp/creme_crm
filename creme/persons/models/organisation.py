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
from django.utils.encoding import smart_str, force_unicode

from django.db.models import ForeignKey, CharField, TextField, PositiveIntegerField, BooleanField, DateField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericRelation
from django.contrib.auth.models import User

from creme_core.models import CremeEntity, Relation, CremePropertyType, CremeProperty
from creme_core.constants import PROP_IS_MANAGED_BY_CREME

from media_managers.models import Image

from address import Address
from contact import Contact
from other_models import StaffSize, LegalForm, Sector
from persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES


class Organisation(CremeEntity):
    name            = CharField(_(u'Name'), max_length=100)
    phone           = CharField(_(u'Phone number'), max_length=100 , blank=True, null=True)
    fax             = CharField(_(u'Fax'), max_length=100 , blank=True, null=True)
    email           = CharField(_(u'Email'), max_length=100 , blank=True, null=True)
    url_site        = CharField(_(u'Web Site'), max_length=100, blank=True, null=True)
    sector          = ForeignKey(Sector, verbose_name=_(u'Sector'), blank=True, null=True)
    capital         = PositiveIntegerField(_(u'Capital'), blank=True, null=True)
    siren           = CharField(_(u'SIREN'), max_length=100, blank=True, null=True)
    naf             = CharField(_(u'NAF code'), max_length=100 , blank=True, null=True)
    siret           = CharField(_(u'SIRET'), max_length=100, blank=True, null=True)
    rcs             = CharField(_(u'RCS/RM'), max_length=100, blank=True, null=True)
    tvaintra        = CharField(_(u'VAT number'), max_length=100, blank=True, null=True)
    subject_to_vat  = BooleanField(_(u'Subject to VAT'), default=True)
    legal_form      = ForeignKey(LegalForm, verbose_name=_(u'Legal form'), blank=True, null=True)
    employees       = ForeignKey(StaffSize, verbose_name=_(u'Staff size'), blank=True, null=True)
    billing_address  = ForeignKey(Address, verbose_name=_(u'Billing address'), blank=True, null=True, related_name='AdressefactuOrganisation_set')
    shipping_address = ForeignKey(Address, verbose_name=_(u'Shipping address'), blank=True, null=True, related_name='AdresselivraisonOrganisation_set')
    annual_revenue  = CharField(_(u'Annual revenue'), max_length=100, blank=True, null=True)
    description     = TextField(_(u'Description'), blank=True, null=True)
    creation_date   = DateField(_(u"Date of creation of the organisation"), blank=True, null=True)
    image           = ForeignKey(Image, verbose_name=_(u'Logo'), blank=True, null=True)

#    addresses = ManyToManyField (Address, verbose_name = _(u'Adresse(s)'),blank=True, null=True, related_name='AdressesOrganisation_set')

    research_fields = CremeEntity.research_fields + ['name']

    class Meta:
        app_label = "persons"
        ordering = ('name',)
        verbose_name = _(u'Organisation')
        verbose_name_plural = _(u'Organisations')

    def save(self):
        self.header_filter_search_field = self.name
        super(Organisation, self).save()

    def __unicode__(self):
        return force_unicode (self.name)

    def get_absolute_url(self):
        return "/persons/organisation/%s" % self.id

    def get_edit_absolute_url(self):
        return "/persons/organisation/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/persons/organisations"

    def get_delete_absolute_url(self):
        return "/persons/organisation/delete/%s" % self.id

    def get_managers(self):
        return Contact.objects.filter(relations__type=REL_SUB_MANAGES, relations__object_entity=self.id)

    def get_employees(self):
        return Contact.objects.filter(relations__type=REL_SUB_EMPLOYED_BY, relations__object_entity=self.id)

    #TODO: used ???
    def zipcode(self):
        if self.billing_address is not None:
            return self.billing_address.zipcode
        return 'Non renseigné'

    @staticmethod
    def get_all_managed_by_creme():
        return Organisation.objects.filter(properties__type=PROP_IS_MANAGED_BY_CREME)
