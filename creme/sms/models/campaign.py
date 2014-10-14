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

from django.db.models import CharField, ManyToManyField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity

from .messaging_list import MessagingList
from .recipient import Recipient


class SMSCampaign(CremeEntity):
    name  = CharField(_(u'Name of the campaign'), max_length=100, blank=False, null=False)
    lists = ManyToManyField(MessagingList, verbose_name=_(u'Related messaging lists'))

    creation_label = _('Add a campaign') #TODO: pgettext (BUT beware because PreferredMenuItem does not manage context currently...)

    class Meta:
        app_label = "sms"
        verbose_name = _(u"SMS campaign")
        verbose_name_plural = _(u"SMS campaigns")
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/sms/campaign/%s" % self.id

    def get_edit_absolute_url(self):
        return "/sms/campaign/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/sms/campaigns"

    def delete(self):
        self.lists.clear()

        for sending in self.sendings.all():
            sending.delete()

        super(SMSCampaign, self).delete()

    def all_recipients(self):
        mlists = self.lists.filter(is_deleted=False)

        #TODO: remove doublons
        #manual recipients
        #recipients = list(number for number in Recipient.objects.filter(messaging_list__id__in=(mlist.id for mlist in lists)).values_list('phone', flat=True))
        recipients = [number for number in Recipient.objects.filter(messaging_list__in=mlists)
                                                            .values_list('phone', flat=True)
                     ]

        #contacts recipients
        recipients.extend(contact.mobile 
                            for mlist in mlists 
                                for contact in mlist.contacts.filter(is_deleted=False)
                                    if contact.mobile
                         )

        return recipients
