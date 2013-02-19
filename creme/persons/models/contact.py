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

#from logging import debug

from django.db.models import (ForeignKey, CharField, TextField, ManyToManyField,
                              DateField, EmailField, ProtectedError, URLField, SET_NULL)
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User

from creme_core.models import CremeEntity, Language
from creme_core.models.fields import PhoneField

from media_managers.models import Image

from address import Address
from other_models import Civility, Position, Sector
from persons.constants import REL_OBJ_EMPLOYED_BY


class Contact(CremeEntity):
    civility        = ForeignKey(Civility, verbose_name=_(u'Civility'), blank=True, null=True, on_delete=SET_NULL)
    last_name       = CharField(_(u'Last name'), max_length=100)
    first_name      = CharField(_(u'First name'), max_length=100, blank=True, null=True)
    description     = TextField(_(u'Description'), blank=True, null=True)
    skype           = CharField('Skype', max_length=100, blank=True, null=True)
    phone           = PhoneField(_(u'Phone number'), max_length=100, blank=True, null=True)
    mobile          = PhoneField(_(u'Mobile'), max_length=100, blank=True, null=True)
    fax             = CharField(_(u'Fax'), max_length=100 , blank=True, null=True)
    position        = ForeignKey(Position, verbose_name=_(u'Position'), blank=True, null=True, on_delete=SET_NULL)
    sector          = ForeignKey(Sector, verbose_name=_(u'Line of business'), blank=True, null=True, on_delete=SET_NULL)
    email           = EmailField(_(u'Email address'), max_length=100, blank=True, null=True)
    url_site        = URLField(_(u'Web Site'), max_length=100, blank=True, null=True, verify_exists=False)
    language        = ManyToManyField(Language, verbose_name=_(u'Spoken language(s)'), blank=True, null=True, editable=False) #TODO: remove this field
    billing_address  = ForeignKey(Address, verbose_name=_(u'Billing address'), blank=True, null=True, related_name='billing_address_contact_set', editable=False) #.set_tags(clonable=False) useless
    shipping_address = ForeignKey(Address, verbose_name=_(u'Shipping address'), blank=True, null=True, related_name='shipping_address_contact_set', editable=False)
    is_user         = ForeignKey(User, verbose_name=_(u'Is an user'), blank=True, null=True, related_name='related_contact', on_delete=SET_NULL, editable=False).set_tags(clonable=False)
    birthday        = DateField(_(u"Birthday"), blank=True, null=True)
    image           = ForeignKey(Image, verbose_name=_(u'Photograph'), blank=True, null=True, on_delete=SET_NULL)

    #research_fields = CremeEntity.research_fields + ['last_name', 'first_name', 'email']
    #_clone_excluded_fields = CremeEntity._clone_excluded_fields | set(['is_user', 'billing_address', 'shipping_address'])
    creation_label = _('Add a contact')

    class Meta:
        app_label = "persons"
        ordering = ('last_name', 'first_name')
        verbose_name = _(u'Contact')
        verbose_name_plural = _(u'Contacts')

    def __unicode__(self):
        if self.civility:
            return u'%s %s %s' % (self.civility, self.first_name, self.last_name)

        return u'%s %s' % (self.first_name, self.last_name)

    def get_employers(self):
        from organisation import Organisation
        return Organisation.objects.filter(relations__type=REL_OBJ_EMPLOYED_BY, relations__object_entity=self.id)

    def get_absolute_url(self):
        return "/persons/contact/%s" % self.id

    def get_edit_absolute_url(self):
        return "/persons/contact/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/persons/contacts"

    def delete(self):
        if self.is_user is not None:
            raise ProtectedError(ugettext(u"A user is associated with this contact."), [self])
        super(Contact, self).delete()

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

        excl_source_addr_ids = filter(None, [source.billing_address_id, source.shipping_address_id])
        for address in Address.objects.filter(object_id=source.id).exclude(pk__in=excl_source_addr_ids):
            address.clone(self)
