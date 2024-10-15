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

import logging
from datetime import date

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core import copying

from . import cloners as billing_cloners
from . import constants
from .core.conversion import Converter
from .models import Base

logger = logging.getLogger(__name__)


class CommonRegularFieldsCopier(copying.FieldsCopierMixin, copying.PreSaveCopier):
    def copy_to(self, target):
        source = self.source

        for field in Base._meta.fields:
            if self.accept(field):
                fname = field.name
                setattr(target, fname, getattr(source, fname))


class CommonManyToManyFieldsCopier(copying.FieldsCopierMixin, copying.PostSaveCopier):
    def copy_to(self, target):
        source = self._source

        for field in Base._meta.many_to_many:
            if self.accept(field):
                field_name = field.name
                getattr(target, field_name).set(getattr(source, field_name).all())


class TitleCopier(copying.PreSaveCopier):
    name_format = _('{src} (converted into {dest._meta.verbose_name})')

    def copy_to(self, target):
        target.name = self.name_format.format(src=self._source, dest=target)


class DatesCopier(copying.PreSaveCopier):
    def copy_to(self, target):
        target.issuing_date = target.expiration_date = date.today()


class QuoteToInvoiceRelationAdder(copying.RelationAdder):
    rtype_id = constants.REL_SUB_INVOICE_FROM_QUOTE


class BillingBaseConverter(Converter):
    pre_save_copiers = [
        *Converter.pre_save_copiers,
        CommonRegularFieldsCopier,
        TitleCopier,
        DatesCopier,
        billing_cloners.EmitterCopier,
        billing_cloners.ReceiverCopier,
    ]
    post_save_copiers = [
        *Converter.post_save_copiers,
        # TODO: unit test
        # NB: useless in vanilla code
        CommonManyToManyFieldsCopier,

        copying.StrongPropertiesCopier,
        copying.StrongRelationsCopier,

        billing_cloners.AddressesCopier,
        billing_cloners.LinesCopier,

        # Does not mean anything to clone that (types are different).
        # CustomFieldsCopier,
    ]

    def _pre_save(self, *, user, source, target):
        super()._pre_save(user=user, source=source, target=target)

        # Do not copy the Addresses of the Receiving Organisation,
        # because we copy the Addresses of the cloned billing entity.
        target._address_auto_copy = False


class InvoiceToQuoteConverter(BillingBaseConverter):
    pass


class QuoteToInvoiceConverter(BillingBaseConverter):
    post_save_copiers = [
        *BillingBaseConverter.post_save_copiers,
        QuoteToInvoiceRelationAdder,
    ]


class QuoteToSalesOrderConverter(BillingBaseConverter):
    pass


class SalesOrderToInvoiceConverter(BillingBaseConverter):
    pass
