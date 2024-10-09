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

from creme.creme_core.core import cloning
from creme.creme_core.models import Relation, RelationType

from . import cloners as billing_cloners
from . import constants
from .core.conversion import Converter
from .models import Base

logger = logging.getLogger(__name__)


class CommonRegularFieldsCopier(cloning.BaseFieldsCopier):
    def copy_to(self, target):
        source = self.source

        for field in Base._meta.fields:
            if self.accept(field):
                fname = field.name
                setattr(target, fname, getattr(source, fname))


class TitleCopier(cloning.BaseFieldsCopier):
    name_format = _('{src} (converted into {dest._meta.verbose_name})')

    def copy_to(self, target):
        target.name = self.name_format.format(src=self._source, dest=target)


class DatesCopier(cloning.Copier):
    def copy_to(self, target):
        target.issuing_date = target.expiration_date = date.today()


class ConversionRelationshipAdder(cloning.Copier):
    # rtype_id = ''  TODO
    # TODO: only (Quote, Invoice)
    rtype_id = constants.REL_SUB_INVOICE_FROM_QUOTE

    def copy_to(self, target):
        assert self.rtype_id
        rtype = RelationType.objects.get(id=self.rtype_id)

        if rtype.enabled:
            Relation.objects.safe_create(
                user=self._user,
                subject_entity=target,
                type=rtype,
                object_entity=self._source,
            )
        else:
            logger.info(
                'Billing conversion: the relation type "%s" is disabled, '
                'no relationship is created.',
                rtype,
            )


class BillingBaseConverter(Converter):
    pre_save_copiers = [
        *Converter.pre_save_copiers,
        CommonRegularFieldsCopier,
        TitleCopier,
        DatesCopier,
        billing_cloners.SourceCopier,
        billing_cloners.TargetCopier,
    ]
    # TODO
    # post_save_copiers = [
    #     # TODO: unit test
    #     # NB: useless in vanilla code
    #     cloning.ManyToManyFieldsCopier,
    #     # Does not mean anything to clone that (types are different).
    #     # CustomFieldsCopier,
    #     # PropertiesCopier,
    #     # RelationsCopier,
    # ]
    post_save_copiers = [
        *Converter.post_save_copiers,
        billing_cloners.AddressesCopier,
        billing_cloners.LinesCopier,
    ]

    def _pre_save(self, *, user, source, target):
        super()._pre_save(user=user, source=source, target=target)
        # target.generate_number_in_create = True  TODO??????

        # Do not copy the Addresses of the Receiving Organisation,
        # because we copy the Addresses of the cloned billing entity.
        target._address_auto_copy = False


# TODO: QuoteToInvoiceConverter
class InvoiceConverter(BillingBaseConverter):
    post_save_copiers = [
        # # TODO: unit test
        # # NB: useless in vanilla code
        # cloning.ManyToManyFieldsCopier,
        # # Does not mean anything to clone that (types are different).
        # # CustomFieldsCopier,
        # # PropertiesCopier,
        # # RelationsCopier,
        *BillingBaseConverter.post_save_copiers,
        ConversionRelationshipAdder,
    ]


class SalesOrderConverter(BillingBaseConverter):
    pass
