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

import datetime  # Easier to mock

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.utils.dates import date_from_ISO8601, date_to_ISO8601

from .core.number_generation import NumberGenerator
from .forms.number_generation import RegularNumberGeneratorItemEditionForm
from .models import NumberGeneratorItem


class RegularNumberGenerator(NumberGenerator):
    form_class = RegularNumberGeneratorItemEditionForm

    # TODO: _default_format() instead?
    @classmethod
    def _default_data(cls):
        return {'format': '{number:04}'}

    @classmethod
    def default_item(cls, organisation, model):
        return NumberGeneratorItem(
            organisation=organisation, numbered_type=model,
            data=cls._default_data(),
        )

    def _build_context(self, item, organisation):
        data = item.data
        counter = data.get('counter', 0) + 1

        today = datetime.date.today()
        year = today.year
        month = today.month

        prev_date_str = data.get('date')
        if prev_date_str:
            # TODO: manage error
            prev_date = date_from_ISO8601(prev_date_str)
            reset = data.get('reset')
            if reset == 'yearly':  # TODO: constant
                if prev_date.year != year:
                    counter = 1
            elif reset == 'monthly':  # TODO: constant
                if prev_date.month != month or prev_date.year != year:
                    counter = 1
            # else: error ??

        # Update item
        data['counter'] = counter
        data['date'] = date_to_ISO8601(today)
        item.data = data

        return {
            'number': counter,  # TODO: <'counter': ...>?
            'year':   year,
            'month':  f'{month:02}',
            'code':   organisation.code,
        }

    # TODO: comment about select_for_update() on invoice/quote/...??
    def perform(self, organisation):
        item = NumberGeneratorItem.objects.filter(
            organisation=organisation,
            numbered_type=ContentType.objects.get_for_model(self._model),
        ).first()

        if item is None:
            return ''

        ctxt = self._build_context(item=item, organisation=organisation)
        item.save()

        # TODO: error
        return item.data['format'].format(**ctxt)


class InvoiceRegularNumberGenerator(RegularNumberGenerator):
    trigger_at_creation = False

    @classmethod
    def _default_data(cls):
        return {'format': _('INV') + '{number:04}'}


class QuoteRegularNumberGenerator(RegularNumberGenerator):
    @classmethod
    def _default_data(cls):
        return {'format': _('QUO') + '{number:04}'}


class SalesOrderRegularNumberGenerator(RegularNumberGenerator):
    @classmethod
    def _default_data(cls):
        return {'format': _('ORD') + '{number:04}'}


class CreditNoteRegularNumberGenerator(RegularNumberGenerator):
    @classmethod
    def _default_data(cls):
        return {'format': _('CN') + '{number:04}'}
