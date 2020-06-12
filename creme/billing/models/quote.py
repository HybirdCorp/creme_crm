# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CREME_REPLACE

from .base import Base
from .other_models import QuoteStatus


class AbstractQuote(Base):
    status = models.ForeignKey(
        QuoteStatus, verbose_name=_('Status of quote'), on_delete=CREME_REPLACE,
    )
    acceptation_date = models.DateField(
        _('Acceptation date'), blank=True, null=True,
    ).set_tags(clonable=False, optional=True)

    creation_label = _('Create a quote')
    save_label     = _('Save the quote')

    search_score = 51

    def get_absolute_url(self):
        return reverse('billing__view_quote', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('billing__create_quote')

    def get_edit_absolute_url(self):
        return reverse('billing__edit_quote', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('billing__list_quotes')

    def build(self, template):
        # Specific recurrent generation rules
        tpl_status_id = template.status_id
        self.status = QuoteStatus.objects.get_or_create(
            pk=tpl_status_id,
            defaults={
                'name': gettext('N/A'),
                'order': tpl_status_id,
            },
        )[0]

        return super().build(template)

    class Meta(Base.Meta):
        abstract = True
        verbose_name = _('Quote')
        verbose_name_plural = _('Quotes')


class Quote(AbstractQuote):
    class Meta(AbstractQuote.Meta):
        swappable = 'BILLING_QUOTE_MODEL'
