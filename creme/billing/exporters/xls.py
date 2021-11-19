# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2021  Hybird
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

from os import path

from django.conf import settings
from django.utils.formats import date_format
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import FileRef
from creme.creme_core.utils.file_handling import FileCreator
from creme.creme_core.utils.secure_filename import secure_filename
from creme.creme_core.utils.xlwt_utils import XlwtWriter

# from .. import constants
from ..models import Line
from . import base


# TODO: use a list sub-exporters in class attribute to facilitate extension/hooking
#       (would be cool to have source/target cached properties before).
class XLSExporter(base.BillingExporter):
    def __init__(self, **kwargs):
        super().__init__(**{
            'verbose_name': _('.xls (data for template)'),
            **kwargs,
        })

    def export(self, entity, user):
        writer = self.get_writer(entity, user)

        basename = secure_filename(f'{entity._meta.verbose_name}_{entity.id}.xls')
        final_path = FileCreator(
            # dir_path=path.join(settings.MEDIA_ROOT, 'upload', 'billing'),
            dir_path=path.join(settings.MEDIA_ROOT, 'billing'),
            name=basename,
        ).create()

        # NB: we create the FileRef instance as soon as possible to get the
        #     smallest duration when a crash causes a file which have to be
        #     removed by hand (not cleaned by the Cleaner job).
        file_ref = FileRef.objects.create(
            user=user,
            # filedata='upload/billing/' + path.basename(final_path),
            filedata='billing/' + path.basename(final_path),
            basename=basename,
        )

        writer.save(final_path)

        return file_ref

    def fill(self, *, writer, entity, user):
        write = writer.writerow

        def address_as_list(address):
            return [
                address.address,
                address.po_box,
                address.zipcode,
                address.city,
                address.department,
                address.state,
                address.country,
            ] if address is not None else []

        source = entity.source
        write([str(source)])
        write(address_as_list(source.billing_address))
        write([source.siret, source.naf, source.rcs, source.tvaintra])

        target = entity.target
        write([str(target)])
        write(address_as_list(target.shipping_address))

        def date_to_str(d):
            return date_format(d, 'DATE_FORMAT') if d else ''

        write([
            date_to_str(entity.issuing_date),
            date_to_str(entity.expiration_date),
        ])

        write(address_as_list(entity.billing_address))
        write(address_as_list(entity.shipping_address))

        # payment_type = getattr(entity, 'payment_type', None)
        payment_type = entity.payment_type
        write([
            entity.number,
            str(payment_type) if payment_type else '',
            getattr(entity, 'buyers_order_number', ''),
        ])

        payment_info = entity.payment_info
        write([
            payment_info.bank_code if payment_info else '',
            payment_info.counter_code if payment_info else '',
            payment_info.account_number if payment_info else '',
            payment_info.rib_key if payment_info else '',
            payment_info.banking_domiciliation if payment_info else '',
        ])

        write([
            str(entity.currency),
            str(entity.discount),
            entity.comment,
        ])

        write([str(entity.total_no_vat), str(entity.total_vat)])

        # TODO: factorise with LineEditForm
        currency_str = entity.currency.local_symbol
        discount_units = {
            # constants.DISCOUNT_PERCENT: '%',
            Line.Discount.PERCENT: '%',
            # constants.DISCOUNT_LINE_AMOUNT: gettext('{currency} per line').format(
            Line.Discount.LINE_AMOUNT: gettext('{currency} per line').format(
                currency=currency_str,
            ),
            # constants.DISCOUNT_ITEM_AMOUNT: gettext('{currency} per unit').format(
            Line.Discount.ITEM_AMOUNT: gettext('{currency} per unit').format(
                currency=currency_str,
            ),
        }

        for line in entity.iter_all_lines():
            item = line.related_item
            write([
                str(item) if item else line.on_the_fly_item,
                str(line.quantity),
                str(line.unit_price),
                str(line.discount),
                discount_units.get(line.discount_unit, '??'),
                str(line.get_raw_price()),
                str(line.get_price_exclusive_of_tax()),
                str(line.get_price_inclusive_of_tax()),
                line.comment,
            ])

    def get_writer(self, entity, user):
        writer = XlwtWriter(encoding='utf-8')
        self.fill(writer=writer, entity=entity, user=user)

        return writer

    @property
    def screenshots(self):
        # yield 'billing/sample_xls.png'
        yield from ()


class XLSExportEngine(base.BillingExportEngine):
    id = base.BillingExportEngine.generate_id('billing', 'xls')

    @property
    def flavours(self):
        yield base.ExporterFlavour.agnostic()

    def exporter(self, flavour):
        return XLSExporter(engine=self, flavour=flavour)
