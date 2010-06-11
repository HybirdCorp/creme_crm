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

from django.db.models import CharField, ManyToManyField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity

from sms.models.sendlist import SendList
from sms.models.recipient import Recipient


class SMSCampaign(CremeEntity):
    name      = CharField(_(u'Nom de la campagne'), max_length=100, blank=False, null=False)
    sendlists = ManyToManyField(SendList, verbose_name=_(u'Listes de diffusion associées'))

    class Meta:
        app_label = "sms"
        verbose_name = _(u"Campagne de SMS")
        verbose_name_plural = _(u"Campagnes de SMS")

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/sms/campaign/%s" % self.id

    def get_edit_absolute_url(self):
        return "/sms/campaign/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/sms/campaigns"

    def get_delete_absolute_url(self):
        return "/sms/campaign/delete/%s" % self.id

    def delete(self):
        self.sendlists.clear()
        
        for sending in self.sendings.all():
            sending.delete()
            
        super(SMSCampaign, self).delete()

    def all_recipients(self):
        lists = self.sendlists.all()

        #manual recipients
        recipients = list(number for number in Recipient.objects.filter(sendlist__id__in=(sendlist.id for sendlist in lists)).values_list('phone', flat=True))

        #contacts recipients
        recipients += list(contact.mobile for sendlist in lists for contact in sendlist.contacts.all() if contact.mobile)

        return recipients
