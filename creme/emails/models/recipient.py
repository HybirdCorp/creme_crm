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

from django.db.models import ForeignKey, CharField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeModel

from mailing_list import MailingList


class EmailRecipient(CremeModel):
    """ A model that stores an e-mail address not linked to a Contact/Organisation"""
    ml      = ForeignKey(MailingList, verbose_name=_(u'Liste de diffusion associée'))
    address = CharField(_(u'Adresse email'), max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.address

    class Meta:
        app_label = "emails"
        verbose_name = _(u'Destinataire')
        verbose_name_plural = _(u'Destinataires')
