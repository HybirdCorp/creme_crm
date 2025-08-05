################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

# import warnings
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity


class AbstractMailingList(CremeEntity):
    name = models.CharField(_('Name of the mailing list'), max_length=80)
    children = models.ManyToManyField(
        settings.EMAILS_MLIST_MODEL,
        verbose_name=_('Child mailing lists'),
        symmetrical=False, related_name='parents_set',
        editable=False,
    )
    contacts = models.ManyToManyField(
        settings.PERSONS_CONTACT_MODEL,
        verbose_name=_('Contact-recipients'),
        editable=False,
    )
    organisations = models.ManyToManyField(
        settings.PERSONS_ORGANISATION_MODEL,
        verbose_name=_('Organisations recipients'),
        editable=False,
    )

    creation_label = _('Create a mailing list')
    save_label     = _('Save the mailing list')

    class Meta:
        abstract = True
        app_label = 'emails'
        verbose_name = _('Mailing list')
        verbose_name_plural = _('Mailing lists')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('emails__view_mlist', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('emails__create_mlist')

    def get_edit_absolute_url(self):
        return reverse('emails__edit_mlist', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('emails__list_mlists')

    def already_in_parents(self, other_ml_id):
        parents = self.parents_set.all()

        for parent in parents:
            if parent.id == other_ml_id:
                return True

        for parent in parents:
            if parent.already_in_parents(other_ml_id):
                return True

        return False

    def already_in_children(self, other_ml_id):
        children = self.children.all()

        for child in children:
            if child.id == other_ml_id:
                return True

        for child in children:
            if child.already_in_children(other_ml_id):
                return True

        return False

    def get_family(self):
        """Return a dictionary<pk: MailingList> with self and all children,
         small children etc...
         """
        family = {}
        self.get_family_aux(family)

        return family

    def get_family_aux(self, dic):
        dic[self.id] = self

        for child in self.children.filter(is_deleted=False):
            child.get_family_aux(dic)

    # def _post_save_clone(self, source):
    #     from .recipient import EmailRecipient
    #
    #     warnings.warn(
    #         'The method MailingList._post_save_clone() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     for recipient in source.emailrecipient_set.all():
    #         EmailRecipient.objects.create(ml=self, address=recipient.address)


class MailingList(AbstractMailingList):
    class Meta(AbstractMailingList.Meta):
        swappable = 'EMAILS_MLIST_MODEL'
