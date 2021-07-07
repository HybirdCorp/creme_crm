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

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import CremeEntity

from .recipient import Recipient


class AbstractSMSCampaign(CremeEntity):
    name = models.CharField(_('Name of the campaign'), max_length=100)
    lists = models.ManyToManyField(
        settings.SMS_MLIST_MODEL,
        verbose_name=_('Related messaging lists'), blank=True,
    )

    creation_label = pgettext_lazy('sms', 'Create a campaign')
    save_label     = pgettext_lazy('sms', 'Save the campaign')

    class Meta:
        abstract = True
        # manager_inheritance_from_future = True
        app_label = 'sms'
        verbose_name = _('SMS campaign')
        verbose_name_plural = _('SMS campaigns')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('sms__view_campaign', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('sms__create_campaign')

    def get_edit_absolute_url(self):
        return reverse('sms__edit_campaign', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('sms__list_campaigns')

    def delete(self, *args, **kwargs):
        self.lists.clear()

        for sending in self.sendings.all():
            sending.delete(*args, **kwargs)

        super().delete(*args, **kwargs)

    # def all_recipients(self):
    def all_phone_numbers(self):
        mlists = self.lists.filter(is_deleted=False)

        # Manual numbers
        recipients = {
            number
            for number in Recipient.objects
                                   .filter(messaging_list__in=mlists)
                                   .values_list('phone', flat=True)
        }

        # Contacts number
        recipients.update(
            contact.mobile
            for mlist in mlists
            for contact in mlist.contacts.filter(is_deleted=False)
            if contact.mobile
        )

        return recipients


class SMSCampaign(AbstractSMSCampaign):
    class Meta(AbstractSMSCampaign.Meta):
        swappable = 'SMS_CAMPAIGN_MODEL'
