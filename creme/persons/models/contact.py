# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from future_builtins import filter
import logging
import warnings

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import (ForeignKey, CharField, TextField, ManyToManyField,
        DateField, EmailField, ProtectedError, URLField, SET_NULL)
from django.db.models.signals import post_save
from django.db.transaction import commit_on_success
from django.db.utils import DatabaseError
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.models import CremeEntity, Language #, CremeEntityManager
from creme.creme_core.models.fields import PhoneField
from creme.creme_core.utils import update_model_instance

from creme.media_managers.models import Image

from ..constants import REL_OBJ_EMPLOYED_BY
from .address import Address
from .other_models import Civility, Position, Sector


logger = logging.getLogger(__name__)


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
    language        = ManyToManyField(Language, verbose_name=_(u'Spoken language(s)'), blank=True, null=True, editable=False).set_tags(viewable=False) #TODO: remove this field
    billing_address  = ForeignKey(Address, verbose_name=_(u'Billing address'),
                                  blank=True, null=True,  editable=False,
                                  related_name='billing_address_contact_set', #TODO: remove ? (with '+')
                                 ).set_tags(enumerable=False) #clonable=False useless
    shipping_address = ForeignKey(Address, verbose_name=_(u'Shipping address'),
                                  blank=True, null=True, editable=False,
                                  related_name='shipping_address_contact_set',
                                 ).set_tags(enumerable=False)
    is_user         = ForeignKey(User, verbose_name=_(u'Related user'), #verbose_name=_(u'Is an user'),
                                 blank=True, null=True, related_name='related_contact',
                                 on_delete=SET_NULL, editable=False
                                ).set_tags(clonable=False, enumerable=False)
    birthday        = DateField(_(u"Birthday"), blank=True, null=True)
    image           = ForeignKey(Image, verbose_name=_(u'Photograph'), blank=True, null=True, on_delete=SET_NULL)

    #objects = CremeEntityManager()
    # Needed because we expand its function fields in other apps (ie. billing)
    #TODO: refactor
    function_fields = CremeEntity.function_fields.new()

    creation_label = _('Add a contact')

    class Meta:
        app_label = "persons"
        ordering = ('last_name', 'first_name')
        verbose_name = _(u'Contact')
        verbose_name_plural = _(u'Contacts')

    def __unicode__(self):
        civ = self.civility

        if civ and civ.shortcut:
#            return u'%s %s %s' % (self.civility.shortcut, self.first_name, self.last_name)
            return ugettext('%(civility)s %(first_name)s %(last_name)s') % {
                        'civility':   civ.shortcut,
                        'first_name': self.first_name,
                        'last_name':  self.last_name,
                    }

        #return u'%s %s' % (self.first_name, self.last_name)
        if self.first_name:
            return ugettext('%(first_name)s %(last_name)s') % {
                            'first_name': self.first_name,
                            'last_name':  self.last_name,
                        }

        return self.last_name

    def _check_deletion(self):
        if self.is_user is not None:
            raise ProtectedError(ugettext(u'A user is associated with this contact.'), [self])

    def clean(self):
        if self.is_user_id:
            if not self.first_name:
                raise ValidationError(ugettext('This Contact is related to a user and must have a first name.'))

            if not self.email:
                raise ValidationError(ugettext('This Contact is related to a user and must have an e-mail address.'))

    def get_employers(self):
        from .organisation import Organisation
        return Organisation.objects.filter(relations__type=REL_OBJ_EMPLOYED_BY, relations__object_entity=self.id)

    def get_absolute_url(self):
        return "/persons/contact/%s" % self.id

    def get_edit_absolute_url(self):
        return "/persons/contact/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/persons/contacts"

    @staticmethod
    def get_user_contact_or_mock(user):
        warnings.warn("Contact.get_user_contact_or_mock() is deprecated ; use User.linked_contact instead.",
                      DeprecationWarning
                     )

        try:
            contact = Contact.objects.get(is_user=user)
        except Contact.DoesNotExist:
            contact = Contact()
        return contact

    def delete(self):
        self._check_deletion() #should not be useful (trashing should be blocked too)
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

    def save(self, *args, **kwargs):
        super(Contact, self).save(*args, **kwargs)

        if self.is_user:
            update_model_instance(self.is_user,
                                  last_name=self.last_name,
                                  first_name=self.first_name or '',
                                  email=self.email or '',
                                 )

    def trash(self):
        self._check_deletion()
        super(Contact, self).trash()


# Manage the related User ------------------------------------------------------

def _create_linked_contact(user):
    return Contact.objects.create(user=user, is_user=user,
                                  last_name=user.last_name or user.username.title(), #TODO: contribute to User to have null=False, blank=False
                                  first_name=user.first_name or _('N/A'), #TODO: idem
                                  email=user.email or _('replaceMe@byYourAddress.com'), #TODO: idem
                                 )

def _get_linked_contact(self):
    contact = getattr(self, '_linked_contact_cache', None)

    if contact is None:
        contacts = Contact.objects.filter(is_user=self)[:2]

        if not contacts:
            logger.critical('User "%s" has no related Contact => we create it', self.username)
            contact = _create_linked_contact(self)
        else:
            if len(contacts) > 1:
                #TODO: repair ? (beware to race condition)
                logger.critical('User "%s" has several related Contacts !', self.username)

            contact = contacts[0]

    self._linked_contact_cache = contact

    return contact

User.linked_contact = property(_get_linked_contact)

@receiver(post_save, sender=User)
def _sync_with_user(sender, instance, created, **kwargs):
    if instance.is_team:
        return

    #when received during 'syncdb' it fails because the Contact table does not exist
    with commit_on_success():
        try:
            if created:
                instance._linked_contact_cache = _create_linked_contact(instance)
            else:
                update_model_instance(instance.linked_contact,
                                      last_name=instance.last_name,
                                      first_name=instance.first_name,
                                      email=instance.email,
                                     )
        except DatabaseError as e:
            logger.warn('Can not create linked contact for this user: %s (if it is the first user,'
                        ' do not worry because it is normal) (%s)', instance, e
                       )
