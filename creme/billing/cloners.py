################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from __future__ import annotations

import logging
import typing

from creme.creme_core.core import copying
from creme.creme_core.core.cloning import EntityCloner
from creme.creme_core.utils.collections import FluentList

if typing.TYPE_CHECKING:
    from .models import Line

logger = logging.getLogger(__name__)


# NB: the cloning & the billing systems both use the words "source" & "target"...
# TODO: rename properties to "emitter" & "receiver"
class EmitterCopier(copying.PreSaveCopier):
    def copy_to(self, target):
        target.source = self._source.source


class ReceiverCopier(copying.PreSaveCopier):
    def copy_to(self, target):
        target.target = self._source.target


# TODO: factorise with persons?
class AddressesCopier(copying.PostSaveCopier):
    address_fields = ['billing_address', 'shipping_address']

    def copy_to(self, target):
        save = False
        source = self._source

        for field_name in self.address_fields:
            source_address = getattr(source, field_name)

            if source_address is not None:
                setattr(target, field_name, source_address.clone(target))
                save = True

        return save


class RelatedItemCopier(copying.PreSaveCopier):
    def copy_to(self, target):
        target.related_item = self.source.related_item


class ReassignedLineCloner(EntityCloner):
    """A kind of Cloner made to clone a line; but the cloned line belongs to
    another document.

    Beware: the API is different from Cloner (the constructor takes an argument).

    See te class <LinesCopier>.
    """
    pre_save_copiers = [
        *EntityCloner.pre_save_copiers,
        RelatedItemCopier,
    ]

    def __init__(self, related_document):
        super().__init__()
        self.related_document = related_document

    def _pre_save(self, *, user, source, target):
        super()._pre_save(user=user, source=source, target=target)
        target.related_document = self.related_document


class LinesCopier(copying.PostSaveCopier):
    line_cloner_classes: dict[type[Line], type[ReassignedLineCloner]] = {}
    default_line_cloner_class = ReassignedLineCloner

    def copy_to(self, target):
        get_cloner_cls = self.line_cloner_classes.get
        default_cloner_class = self.default_line_cloner_class
        user = self._user

        for line in self._source.iter_all_lines():
            cloner_cls = get_cloner_cls(type(line), default_cloner_class)
            cloner_cls(related_document=target).perform(user=user, entity=line)


class BillingBaseCloner(EntityCloner):
    pre_save_copiers = [
        *EntityCloner.pre_save_copiers,
        EmitterCopier,
        ReceiverCopier,
    ]
    post_save_copiers = [
        *EntityCloner.post_save_copiers,
        AddressesCopier,
        LinesCopier,
    ]

    def _pre_save(self, *, user, source, target):
        super()._pre_save(user=user, source=source, target=target)
        # Do not copy the Addresses of the Receiving Organisation,
        # because we copy the Addresses of the cloned billing entity.
        target._address_auto_copy = False


class InvoiceFieldsCopier(copying.RegularFieldsCopier):
    # TODO: what about "issuing_date"? should we copy it?
    # NB: the cloned Invoice uses the default status
    exclude = {'status'}


class InvoiceCloner(BillingBaseCloner):
    pre_save_copiers = FluentList(
        BillingBaseCloner.pre_save_copiers
    ).replace(old=copying.RegularFieldsCopier, new=InvoiceFieldsCopier)


class QuoteCloner(BillingBaseCloner):
    pass


class SalesOrderCloner(BillingBaseCloner):
    pass


class CreditNoteCloner(BillingBaseCloner):
    pass
