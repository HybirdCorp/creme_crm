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

from django.db.models import (ForeignKey, CharField, TextField, PositiveIntegerField,
                              BooleanField, DateField, EmailField, URLField, SET_NULL)
from django.utils.translation import ugettext_lazy as _, ugettext
from django.core.exceptions import ValidationError

from creme.creme_core.models import CremeEntity
from creme.creme_core.models.fields import PhoneField
from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME

from creme.media_managers.models import Image

from ..constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
from .contact import Contact
from .address import Address
from .other_models import StaffSize, LegalForm, Sector


class Organisation(CremeEntity):
    name            = CharField(_(u'Name'), max_length=100)
    phone           = PhoneField(_(u'Phone number'), max_length=100 , blank=True, null=True)
    fax             = CharField(_(u'Fax'), max_length=100 , blank=True, null=True)
    email           = EmailField(_(u'Email address'), max_length=100 , blank=True, null=True)
    url_site        = URLField(_(u'Web Site'), max_length=100, blank=True, null=True, verify_exists=False)
    sector          = ForeignKey(Sector, verbose_name=_(u'Sector'), blank=True, null=True, on_delete=SET_NULL)
    capital         = PositiveIntegerField(_(u'Capital'), blank=True, null=True)
    siren           = CharField(_(u'SIREN'), max_length=100, blank=True, null=True)
    naf             = CharField(_(u'NAF code'), max_length=100 , blank=True, null=True)
    siret           = CharField(_(u'SIRET'), max_length=100, blank=True, null=True)
    rcs             = CharField(_(u'RCS/RM'), max_length=100, blank=True, null=True)
    tvaintra        = CharField(_(u'VAT number'), max_length=100, blank=True, null=True)
    subject_to_vat  = BooleanField(_(u'Subject to VAT'), default=True)
    legal_form      = ForeignKey(LegalForm, verbose_name=_(u'Legal form'), blank=True, null=True, on_delete=SET_NULL)
    staff_size      = ForeignKey(StaffSize, verbose_name=_(u'Staff size'), blank=True, null=True, on_delete=SET_NULL)
    billing_address  = ForeignKey(Address, verbose_name=_(u'Billing address'), blank=True, null=True, related_name='billing_address_orga_set', editable=False) #.set_tags(clonable=False) useless
    shipping_address = ForeignKey(Address, verbose_name=_(u'Shipping address'), blank=True, null=True, related_name='shipping_address_orga_set', editable=False)
    annual_revenue  = CharField(_(u'Annual revenue'), max_length=100, blank=True, null=True)
    description     = TextField(_(u'Description'), blank=True, null=True)
    creation_date   = DateField(_(u"Date of creation of the organisation"), blank=True, null=True)
    image           = ForeignKey(Image, verbose_name=_(u'Logo'), blank=True, null=True)

    #research_fields = CremeEntity.research_fields + ['name']
    #_clone_excluded_fields = CremeEntity._clone_excluded_fields | set(['billing_address', 'shipping_address'])
    creation_label = _('Add an organisation')

    class Meta:
        app_label = "persons"
        ordering = ('name',)
        verbose_name = _(u'Organisation')
        verbose_name_plural = _(u'Organisations')

    def __unicode__(self):
        return self.name

    # TODO create an empty_or_unique custom model field to handle unique field case properly
    # TODO override validate method of this custom model field to fix validation error display in forms (global -> field)
    # TODO modify the bulk update registry to manage empty or unique fields using instance of this futur custom model field ??

    # TODO Validation error is displayed twice in the global errors block
    def clean(self, *args, **kwargs):
        super(Organisation, self).clean(*args, **kwargs)
        siren = self.siren
        if siren:
            qs = Organisation.objects.filter(siren=siren)
            self_pk = self.pk
            if self_pk:
                qs = qs.exclude(pk=self_pk)
            if qs.exists():
                raise ValidationError(ugettext(u"This siren already exists and must be unique !"))

    def get_absolute_url(self):
        return "/persons/organisation/%s" % self.id

    def get_edit_absolute_url(self):
        return "/persons/organisation/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/persons/organisations"

    def get_managers(self):
        return Contact.objects.filter(is_deleted=False,
                                      relations__type=REL_SUB_MANAGES,
                                      relations__object_entity=self.id,
                                     )

    def get_employees(self):
        return Contact.objects.filter(is_deleted=False,
                                      relations__type=REL_SUB_EMPLOYED_BY,
                                      relations__object_entity=self.id,
                                     )

    @staticmethod
    def get_all_managed_by_creme():
        return Organisation.objects.filter(is_deleted=False,
                                           properties__type=PROP_IS_MANAGED_BY_CREME,
                                          )

    #TODO: factorise with Contact (move in a base abstract class ?)
    def _post_save_clone(self, source):
        save = False

        if source.billing_address is not None:
            self.billing_address = source.billing_address.clone(self)
            save = True

        if source.shipping_address is not None:
            self.shipping_address = source.shipping_address.clone(self)
            save = True

        if save:
            self.save()

        #TODO: factorise with OtherAdressesBlock ??
        excl_source_addr_ids = filter(None, [source.billing_address_id, source.shipping_address_id])

        for address in Address.objects.filter(object_id=source.id).exclude(pk__in=excl_source_addr_ids):
            address.clone(self)
