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

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CremeEntity

from .recipient import EmailRecipient


class AbstractEmailCampaign(CremeEntity):
    name = models.CharField(_('Name of the campaign'), max_length=100)
    mailing_lists = models.ManyToManyField(
        settings.EMAILS_MLIST_MODEL,
        blank=True, verbose_name=_('Related mailing lists'),
    )

    creation_label = _('Create an emailing campaign')
    save_label     = _('Save the emailing campaign')

    class Meta:
        abstract = True
        app_label = 'emails'
        verbose_name = _('Emailing campaign')
        verbose_name_plural = _('Emailing campaigns')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('emails__view_campaign', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('emails__create_campaign')

    def get_edit_absolute_url(self):
        return reverse('emails__edit_campaign', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('emails__list_campaigns')

    def all_recipients(self):
        # Merge all the mailing_lists and their children
        lists = {
            pk: ml
            for ml in self.mailing_lists.filter(is_deleted=False)
            for pk, ml in ml.get_family().items()
        }.values()

        # Manual recipients
        recipients = {
            addr: None
            for addr in EmailRecipient.objects
                                      .filter(ml__in=[ml.id for ml in lists])
                                      .values_list('address', flat=True)
        }

        # Contacts & organisations recipients
        def update(get_persons):
            recipients.update(
                (p.email, p)
                for ml in lists
                for p in get_persons(ml).filter(is_deleted=False)
                if p.email
            )

        update(lambda ml: ml.contacts)
        update(lambda ml: ml.organisations)

        return recipients.items()

    def restore(self):
        super().restore()

        # TODO: in a signal handler instead ?
        #       (we need a restore signal, or an official "backup" feature -- see HistoryLine)
        from .sending import EmailSending

        if EmailSending.objects.filter(campaign=self).exclude(
            state=EmailSending.State.DONE,
        ).exists():
            # TODO: regroup the 'refresh' message, to avoid flooding the job manager
            from ..creme_jobs import campaign_emails_send_type

            campaign_emails_send_type.refresh_job()


class EmailCampaign(AbstractEmailCampaign):
    class Meta(AbstractEmailCampaign.Meta):
        swappable = 'EMAILS_CAMPAIGN_MODEL'
