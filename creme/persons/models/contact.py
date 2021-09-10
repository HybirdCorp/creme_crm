# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.core.exceptions import SpecificProtectedError
from creme.creme_core.models import CREME_REPLACE_NULL, CremeEntity, Language
from creme.creme_core.models.fields import PhoneField
from creme.creme_core.utils import update_model_instance
from creme.documents.models.fields import ImageEntityForeignKey

from .. import constants, get_contact_model, get_organisation_model
from . import other_models
from .base import PersonWithAddressesMixin

logger = logging.getLogger(__name__)


class AbstractContact(CremeEntity, PersonWithAddressesMixin):
    civility = models.ForeignKey(
        other_models.Civility,
        verbose_name=_('Civility'),
        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
    )
    # NB: same max_length than CremeUser.last_name
    last_name = models.CharField(_('Last name'), max_length=100)
    # NB: same max_length than CremeUser.first_name
    first_name = models.CharField(_('First name'), max_length=100, blank=True)

    skype    = models.CharField('Skype', max_length=100, blank=True).set_tags(optional=True)
    phone    = PhoneField(_('Phone number'), max_length=100, blank=True).set_tags(optional=True)
    mobile   = PhoneField(_('Mobile'), max_length=100, blank=True).set_tags(optional=True)
    fax      = models.CharField(_('Fax'), max_length=100, blank=True).set_tags(optional=True)
    email    = models.EmailField(_('Email address'), blank=True).set_tags(optional=True)
    url_site = models.URLField(_('Web Site'), max_length=500, blank=True).set_tags(optional=True)

    position = models.ForeignKey(
        other_models.Position,
        verbose_name=_('Position'),
        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
    ).set_tags(optional=True)
    full_position = models.CharField(
        _('Detailed position'), max_length=500, blank=True,
    ).set_tags(optional=True)

    sector = models.ForeignKey(
        other_models.Sector,
        verbose_name=_('Line of business'),
        blank=True, null=True, on_delete=CREME_REPLACE_NULL,
    ).set_tags(optional=True)

    # language = models.ManyToManyField(
    languages = models.ManyToManyField(
        Language,
        verbose_name=_('Spoken language(s)'),
        blank=True,  # editable=False,
    ).set_tags(optional=True)  # viewable=False

    is_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('Related user'),
        blank=True, null=True,
        related_name='related_contact', on_delete=models.SET_NULL,
        editable=False,
    ).set_tags(clonable=False).set_null_label(pgettext_lazy('persons-is_user', 'None'))

    birthday = models.DateField(_('Birthday'), blank=True, null=True).set_tags(optional=True)

    image = ImageEntityForeignKey(
        verbose_name=_('Photograph'), blank=True, null=True, on_delete=models.SET_NULL,
    ).set_tags(optional=True)

    search_score = 101

    creation_label = _('Create a contact')
    save_label     = _('Save the contact')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'persons'
        ordering = ('last_name', 'first_name')
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')
        index_together = ('last_name', 'first_name', 'cremeentity_ptr')

    def __str__(self):
        civ = self.civility

        if civ and civ.shortcut:
            return gettext('{civility} {first_name} {last_name}').format(
                civility=civ.shortcut,
                first_name=self.first_name,
                last_name=self.last_name,
            )

        if self.first_name:
            return gettext('{first_name} {last_name}').format(
                first_name=self.first_name,
                last_name=self.last_name,
            )

        return self.last_name or ''

    def _check_deletion(self):
        if self.is_user is not None:
            raise SpecificProtectedError(
                gettext('A user is associated with this contact.'),
                [self]
            )

    def clean(self):
        if self.is_user_id:
            if not self.first_name:
                raise ValidationError(
                    gettext('This Contact is related to a user and must have a first name.')
                )

            if not self.email:
                raise ValidationError(
                    gettext('This Contact is related to a user and must have an e-mail address.')
                )

    def delete(self, *args, **kwargs):
        self._check_deletion()  # Should not be useful (trashing should be blocked too)
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('persons__view_contact', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('persons__create_contact')

    def get_edit_absolute_url(self):
        return reverse('persons__edit_contact', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('persons__list_contacts')

    # TODO: use FilteredRelation ?
    def get_employers(self) -> models.QuerySet:
        return get_organisation_model().objects.filter(
            is_deleted=False,
            relations__type__in=(constants.REL_OBJ_EMPLOYED_BY, constants.REL_OBJ_MANAGES),
            relations__object_entity=self.id,
        )

    def _post_save_clone(self, source):
        self._aux_post_save_clone(source)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        rel_user = self.is_user
        if rel_user:
            rel_user._disable_sync_with_contact = True

            update_model_instance(
                rel_user,
                last_name=self.last_name,
                first_name=self.first_name or '',
                email=self.email or '',
            )

    def trash(self):
        self._check_deletion()
        super().trash()

    @classmethod
    def _create_linked_contact(cls, user, **kwargs) -> 'AbstractContact':
        # TODO: assert user is not a team + enforce non team clean() ?
        owner = user

        if user.is_staff:
            superuser = type(user)._default_manager.filter(
                is_superuser=True, is_staff=False,
            ).order_by('id').first()

            if superuser is None:
                logger.critical(
                    'No existing super-user found to assign the staff Contact '
                    '(creme_populate has not been run?!) ; you should create a '
                    'super-user & change the owner of this staff Contact in '
                    'order to avoid some broken behaviours (eg: inner-edition '
                    'fails).'
                )
            else:
                owner = superuser

        return cls.objects.create(
            user=owner,
            is_user=user,
            last_name=user.last_name or user.username.title(),
            first_name=user.first_name or _('N/A'),
            email=user.email or _('complete@Me.com'),
            **kwargs
        )


class Contact(AbstractContact):
    class Meta(AbstractContact.Meta):
        swappable = 'PERSONS_CONTACT_MODEL'


# Manage the related User ------------------------------------------------------

def _get_linked_contact(self):
    if self.is_team:
        return None

    contact = getattr(self, '_linked_contact_cache', None)

    if contact is None:
        model = get_contact_model()
        contacts = model.objects.filter(is_user=self)[:2]

        if not contacts:
            logger.critical(
                'User "%s" has no related Contact => we create it',
                self.username,
            )
            contact = model._create_linked_contact(self)
        else:
            if len(contacts) > 1:
                # TODO: repair ? (beware to race condition)
                logger.critical(
                    'User "%s" has several related Contacts !',
                    self.username,
                )

            contact = contacts[0]

    self._linked_contact_cache = contact

    return contact
