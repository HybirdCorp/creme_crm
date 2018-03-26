# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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
from django.db.models import ForeignKey, CharField, CASCADE
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeModel


class Recipient(CremeModel):
    """ A model that stores a phone number not linked to a Contact"""
    messaging_list = ForeignKey(settings.SMS_MLIST_MODEL, verbose_name=_(u'Related messaging list'), on_delete=CASCADE)
    phone          = CharField(_(u'Number'), max_length=100, blank=True)

    creation_label   = _(u'Add a recipient')
    save_label       = _(u'Save the recipient')
    multi_save_label = _(u'Save the recipients')

    class Meta:
        app_label = 'sms'
        verbose_name = _(u'Recipient')
        verbose_name_plural = _(u'Recipients')
        # ordering = ('phone',) TODO ??

    def __unicode__(self):
        return self.phone

    def get_related_entity(self):  # For generic views
        return self.messaging_list

    def clone(self, messaging_list):
        return Recipient.objects.create(messaging_list=messaging_list, phone=self.phone)
