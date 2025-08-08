################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025 Hybird
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
from datetime import date, timedelta

from django.utils.translation import gettext

from creme.creme_core.core.copying import PreSaveCopier
from creme.creme_core.utils.collections import FluentList

from . import cloners as billing_cloners
from .core.spawning import Spawner

logger = logging.getLogger(__name__)


class NumberCopier(PreSaveCopier):
    def copy_to(self, target):
        target.number = self._source.number


class StatusCopier(PreSaveCopier):
    def copy_to(self, target):
        status_model = type(target)._meta.get_field('status').remote_field.model
        target.status = (
            status_model.objects.filter(uuid=self._source.status_uuid).first()
            or status_model.objects.default()
        )


# TODO: the code would be more simpler if we had one not custom status...
class QuoteStatusCopier(PreSaveCopier):
    def copy_to(self, target):
        status_model = type(target)._meta.get_field('status').remote_field.model
        source = self._source

        status = status_model.objects.filter(uuid=source.status_uuid).first()
        if status is None:
            logger.warning('Invalid status UUID in TemplateBase(id=%s)', source.id)

            status = status_model.objects.order_by('-is_default').first()
            if status is None:
                logger.warning('TemplateBase: no Quote Status available, so we create one')
                status = status_model.objects.create(name=gettext('N/A'))

        target.status = status


# TODO: do not mark 'Base.additional_info' as <clonable=False> (just exclude in cloner)?
class AdditionalInfoCopier(PreSaveCopier):
    def copy_to(self, target):
        target.additional_info = self._source.additional_info


# TODO: same remark
class PaymentTermsCopier(PreSaveCopier):
    def copy_to(self, target):
        target.payment_terms = self._source.payment_terms


class DatesCopier(PreSaveCopier):
    def copy_to(self, target):
        target.issuing_date = date.today()
        # TODO: user configurable rules?
        target.expiration_date = target.issuing_date + timedelta(days=30)


class BillingBaseSpawner(Spawner):
    pre_save_copiers = [
        *Spawner.pre_save_copiers,
        NumberCopier,
        StatusCopier,
        DatesCopier,
        billing_cloners.EmitterCopier,
        billing_cloners.ReceiverCopier,
        AdditionalInfoCopier,
        PaymentTermsCopier,
    ]
    post_save_copiers = [
        *Spawner.post_save_copiers,
        billing_cloners.AddressesCopier,
        billing_cloners.LinesCopier,
    ]

    def _pre_save(self, *, user, source, target):
        super()._pre_save(user=user, source=source, target=target)
        target.generate_number_in_create = True

        # Do not copy the Addresses of the Receiving Organisation,
        # because we copy the Addresses of the cloned billing entity.
        target._address_auto_copy = False


class InvoiceSpawner(BillingBaseSpawner):
    pass


class QuoteSpawner(BillingBaseSpawner):
    pre_save_copiers = FluentList(
        BillingBaseSpawner.pre_save_copiers
    ).replace(old=StatusCopier, new=QuoteStatusCopier)


class SalesOrderSpawner(BillingBaseSpawner):
    pass


class CreditNoteSpawner(BillingBaseSpawner):
    pass
