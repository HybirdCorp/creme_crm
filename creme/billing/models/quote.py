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

# import warnings
import logging

from django.db import models
from django.urls import reverse
# from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import CREME_REPLACE

# from .. import get_template_base_model
from .base import Base
from .other_models import QuoteStatus, get_default_quote_status_pk

logger = logging.getLogger(__name__)


class AbstractQuote(Base):
    status = models.ForeignKey(
        QuoteStatus,
        verbose_name=_('Status of quote'),
        on_delete=CREME_REPLACE,
        default=get_default_quote_status_pk,
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

    # def build(self, template):
    #     warnings.warn(
    #         'The method billing.models.Quote.build() is deprecated.',
    #         DeprecationWarning,
    #     )
    #
    #     status = None
    #
    #     if isinstance(template, get_template_base_model()):
    #         status = QuoteStatus.objects.filter(uuid=template.status_uuid).first()
    #         if status is None:
    #             logger.warning('Invalid status UUID in TemplateBase(id=%s)', template.id)
    #
    #     if status is None:
    #         status = QuoteStatus.objects.order_by('-is_default').first()
    #         if status is None:
    #             logger.warning('TemplateBase: no Quote Status available, so we create one')
    #             status = QuoteStatus.objects.create(name=gettext('N/A'))
    #
    #     self.status = status
    #
    #     return super().build(template)

    class Meta(Base.Meta):
        abstract = True
        verbose_name = _('Quote')
        verbose_name_plural = _('Quotes')


class Quote(AbstractQuote):
    class Meta(AbstractQuote.Meta):
        swappable = 'BILLING_QUOTE_MODEL'
