# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from mailing_list import MailingList
from recipient import EmailRecipient


class EmailCampaign(CremeEntity):
    name          = CharField(_(u'Name of the campaign'), max_length=100, blank=False, null=False)
    mailing_lists = ManyToManyField(MailingList, verbose_name=_(u'Related mailing lists'))

    class Meta:
        app_label = "emails"
        verbose_name = _(u"Emailing campaign")
        verbose_name_plural = _(u"Emailing campaigns")

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/emails/campaign/%s" % self.id

    def get_edit_absolute_url(self):
        return "/emails/campaign/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/emails/campaigns"

    #def delete(self):
        #for sending in self.sendings_set.all():
            #sending.mails_set.all().delete() #todo: useful (already done in Sending.delete()) ??  #use CremeModel delete() ??
            #sending.delete()

        #super(EmailCampaign, self).delete()

    def all_recipients(self):
        #merge all the mailing_lists and their children
        lists = dict(pk_ml for ml in self.mailing_lists.all() for pk_ml in ml.get_family().iteritems()).values()

        #manual recipients
        recipients = dict((addr, None) for addr in EmailRecipient.objects.filter(ml__in=[ml.id for ml in lists]) \
                                                                         .values_list('address', flat=True)
                         )

        #contacts & organisations recipients
        recipients.update((contact.email, contact) for ml in lists for contact in ml.contacts.all()      if contact.email)
        recipients.update((orga.email,    orga)    for ml in lists for orga    in ml.organisations.all() if orga.email)

        return recipients.iteritems()