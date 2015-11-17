# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
from django.core.urlresolvers import reverse
from django.db.models import CharField, ManyToManyField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity

#from .mailing_list import MailingList
from .recipient import EmailRecipient


#class EmailCampaign(CremeEntity):
class AbstractEmailCampaign(CremeEntity):
    name          = CharField(_(u'Name of the campaign'), max_length=100, blank=False, null=False)
#    mailing_lists = ManyToManyField(MailingList, verbose_name=_(u'Related mailing lists'))
    mailing_lists = ManyToManyField(settings.EMAILS_MLIST_MODEL, verbose_name=_(u'Related mailing lists'))

    creation_label = _('Add an emailing campaign')

    class Meta:
        abstract = True
        app_label = "emails"
        verbose_name = _(u"Emailing campaign")
        verbose_name_plural = _(u"Emailing campaigns")
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
#        return "/emails/campaign/%s" % self.id
        return reverse('emails__view_campaign', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('emails__create_campaign')

    def get_edit_absolute_url(self):
#        return "/emails/campaign/edit/%s" % self.id
        return reverse('emails__edit_campaign', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
#        return "/emails/campaigns"
        return reverse('emails__list_campaigns')

    def all_recipients(self):
        #merge all the mailing_lists and their children
        lists = dict(pk_ml for ml in self.mailing_lists.filter(is_deleted=False)
                        for pk_ml in ml.get_family().iteritems()
                    ).values()

        #manual recipients
        recipients = {addr: None
                          for addr in EmailRecipient.objects.filter(ml__in=[ml.id for ml in lists])
                                                            .values_list('address', flat=True)
                     }

        #contacts & organisations recipients
        def update(get_persons):
            recipients.update((p.email, p)
                                for ml in lists
                                    for p in get_persons(ml).filter(is_deleted=False)
                                        if p.email
                             )

        update(lambda ml: ml.contacts)
        update(lambda ml: ml.organisations)

        return recipients.iteritems()


class EmailCampaign(AbstractEmailCampaign):
    class Meta(AbstractEmailCampaign.Meta):
        swappable = 'EMAILS_CAMPAIGN_MODEL'
