################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

import datetime

from django.db.models import TextChoices
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.utils.dates import date_from_ISO8601, date_to_ISO8601

from .core.number_generation import NumberGenerator
from .forms.number_generation import RegularNumberGeneratorItemEditionForm


class ResetType(TextChoices):
    NEVER   = 'never',   pgettext_lazy('billing-reset', 'Never'),
    MONTHLY = 'monthly', _('Monthly'),
    YEARLY  = 'yearly',  _('Yearly'),


class RegularNumberGenerator(NumberGenerator):
    form_class = RegularNumberGeneratorItemEditionForm

    @classmethod
    def _default_data(cls):
        return {
            'format': cls._default_format(),
            'reset': ResetType.NEVER,
        }

    @classmethod
    def _default_format(cls):
        return '{counter:04}'

    def _build_context(self, item):
        data = item.data
        counter = data.get('counter', 1)

        today = datetime.date.today()
        year = today.year
        month = today.month

        prev_date_str = data.get('date')
        if prev_date_str:
            # TODO: manage error
            prev_date = date_from_ISO8601(prev_date_str)
            reset = data.get('reset')
            if reset == ResetType.YEARLY:
                if prev_date.year != year:
                    counter = 1
            elif reset == ResetType.MONTHLY:
                if prev_date.month != month or prev_date.year != year:
                    counter = 1
            # else: error ??

        # Update item
        data['counter'] = counter + 1
        data['date'] = date_to_ISO8601(today)
        item.data = data

        return {
            'counter': counter,
            'year':   year,
            'month':  f'{month:02}',
            'code':   item.organisation.code,
        }

    def perform(self):
        item = self._item

        try:
            number = item.data['format'].format(**self._build_context(item=item))
        except Exception as e:
            raise ConflictError(
                _('An error occurred when generating the number (original error: {})').format(e)
            )

        item.save()

        return number

    @property
    def description(self):
        data = self._item.data

        return [
            *super().description,

            gettext('Pattern: «{}»').format(data['format']),
            gettext('Current counter: {}').format(data.get('counter', 1)),
            gettext('Counter reset: {}').format(ResetType(data['reset']).label),
        ]


class InvoiceRegularNumberGenerator(RegularNumberGenerator):
    @classmethod
    def _default_format(cls):
        return gettext('INV') + '-{year}-{month}-{counter:04}'


class QuoteRegularNumberGenerator(RegularNumberGenerator):
    @classmethod
    def _default_format(cls):
        return gettext('QUO') + '-{year}-{month}-{counter:04}'


class SalesOrderRegularNumberGenerator(RegularNumberGenerator):
    @classmethod
    def _default_format(cls):
        return gettext('ORD') + '-{year}-{month}-{counter:04}'


class CreditNoteRegularNumberGenerator(RegularNumberGenerator):
    @classmethod
    def _default_format(cls):
        return gettext('CN') + '-{year}-{month}-{counter:04}'
