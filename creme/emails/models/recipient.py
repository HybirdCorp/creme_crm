################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import CremeModel


class EmailRecipient(CremeModel):
    """A model which stores an email address not linked to a Contact/Organisation."""
    ml = models.ForeignKey(
        settings.EMAILS_MLIST_MODEL,
        on_delete=models.CASCADE, verbose_name=_('Related mailing list'),
    )
    address = models.CharField(_('Email address'), max_length=100)

    creation_label   = pgettext_lazy('emails', 'Add a recipient')
    save_label       = pgettext_lazy('emails', 'Save the recipient')
    multi_save_label = pgettext_lazy('emails', 'Save the recipients')

    class Meta:
        app_label = 'emails'
        verbose_name = pgettext_lazy('emails', 'Recipient')
        verbose_name_plural = pgettext_lazy('emails', 'Recipients')
        ordering = ('address',)

    def __str__(self):
        return self.address

    def get_related_entity(self):  # For generic views
        return self.ml
