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

from django.db.models import ForeignKey, CharField, TextField, ManyToManyField, DateField
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.encoding import force_unicode
from django.contrib.auth.models import User

from creme_core.models.entity import CremeEntity
from creme_core.models.i18n import Language

from media_managers.models import Image

from address import Address
from other_models import Civility, PeopleFunction, Sector

from persons.constants import REL_OBJ_EMPLOYED_BY


class Contact(CremeEntity):
    civility        = ForeignKey(Civility, verbose_name=_(u'Civility'), blank=True, null=True)
    first_name      = CharField(_(u'First name'), max_length=100)
    last_name       = CharField(_(u'Last name'), max_length=100)
    description     = TextField(_(u'Description'), blank=True, null=True)
    skype           = CharField('Skype', max_length=100, blank=True, null=True)
    landline        = CharField(_(u'Landline'), max_length=100, blank=True, null=True)
    mobile          = CharField(_(u'Mobile'), max_length=100, blank=True, null=True)
    fax             = CharField(_(u'Fax'), max_length=100 , blank=True, null=True)
    function        = ForeignKey(PeopleFunction, verbose_name=_(u'Position'), blank=True, null=True)
    sector          = ForeignKey(Sector, verbose_name=_(u'Line of business'), blank=True, null=True)
    email           = CharField(_(u'Email'), max_length=100, blank=True, null=True)
    url_site        = CharField(_(u'Web Site'), max_length=100, blank=True, null=True)
    language        = ManyToManyField(Language, verbose_name=_(u'Spoken language(s)'), blank=True, null=True, related_name='ContactLanguages_set')
    billing_address  = ForeignKey(Address, verbose_name=_(u'Billing address'), blank=True, null=True, related_name='AdressefactuContact_set')
    shipping_address = ForeignKey(Address, verbose_name=_(u'Shipping address'), blank=True, null=True, related_name='AdresselivraisonContact_set')
    is_user         = ForeignKey(User, verbose_name=_(u'Is an user'), blank=True, null=True, related_name='contact_est_user_set')
    birthday        = DateField(_(u"Birthday"), blank=True, null=True)
    image           = ForeignKey(Image, verbose_name=_(u'Photograph'), blank=True, null=True)

    research_fields = CremeEntity.research_fields + ['last_name', 'first_name', 'email']

    class Meta:
        app_label = "persons"
        ordering = ('last_name', 'first_name')
        verbose_name = _(u'Contact')
        verbose_name_plural = _(u'Contacts')

    #def get_entity_actions(self):
        #return """<a href="%s">Voir</a> | <a href="%s">Éditer</a> | <a href="%s" onclick="creme.utils.confirmDelete(event, this);">Effacer</a>""" \
                #% (self.get_absolute_url(), self.get_edit_absolute_url(), self.get_delete_absolute_url())

    def save(self, *args, **kwargs):
        self.header_filter_search_field = u"%s %s %s" % (self.civility, self.first_name, self.last_name)
        super(Contact, self).save(*args, **kwargs)

    def get_employers(self):
        from organisation import Organisation
        return Organisation.objects.filter(relations__type=REL_OBJ_EMPLOYED_BY, relations__object_entity=self.id)

    def __unicode__(self):
        try:
            return force_unicode(u'%s %s %s' % (self.civility or "" , self.first_name, self.last_name))
        except Exception, e: #TODO: useful ??
            debug('Exception in Contact.__unicode__: %s', e)

    def get_absolute_url(self):
        return "/persons/contact/%s" % self.id

    def get_edit_absolute_url(self):
        return "/persons/contact/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/persons/contacts"

    def get_delete_absolute_url(self):
        return "/persons/contact/delete/%s" % self.id

    def delete(self):
        #TODO: Make a view to 'say' that can't be deleted
        if self.is_user is None:
            super(Contact, self).delete()