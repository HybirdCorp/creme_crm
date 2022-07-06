################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2022  Hybird
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

from creme.creme_core import get_concrete_model


def credit_note_model_is_custom():
    return (
        settings.BILLING_CREDIT_NOTE_MODEL != 'billing.CreditNote'
        and not settings.BILLING_CREDIT_NOTE_FORCE_NOT_CUSTOM
    )


def invoice_model_is_custom():
    return (
        settings.BILLING_INVOICE_MODEL != 'billing.Invoice'
        and not settings.BILLING_INVOICE_FORCE_NOT_CUSTOM
    )


def product_line_model_is_custom():
    return (
        settings.BILLING_PRODUCT_LINE_MODEL != 'billing.ProductLine'
        and not settings.BILLING_PRODUCT_LINE_FORCE_NOT_CUSTOM
    )


def quote_model_is_custom():
    return (
        settings.BILLING_QUOTE_MODEL != 'billing.Quote'
        and not settings.BILLING_QUOTE_FORCE_NOT_CUSTOM
    )


def sales_order_model_is_custom():
    return (
        settings.BILLING_SALES_ORDER_MODEL != 'billing.SalesOrder'
        and not settings.BILLING_SALES_ORDER_FORCE_NOT_CUSTOM
    )


def service_line_model_is_custom():
    return (
        settings.BILLING_SERVICE_LINE_MODEL != 'billing.ServiceLine'
        and not settings.BILLING_SERVICE_LINE_FORCE_NOT_CUSTOM
    )


def template_base_model_is_custom():
    return (
        settings.BILLING_TEMPLATE_BASE_MODEL != 'billing.TemplateBase'
        and not settings.BILLING_TEMPLATE_BASE_FORCE_NOT_CUSTOM
    )


def get_credit_note_model():
    """Returns the CreditNote model that is active in this project."""
    return get_concrete_model('BILLING_CREDIT_NOTE_MODEL')


def get_invoice_model():
    """Returns the Invoice model that is active in this project."""
    return get_concrete_model('BILLING_INVOICE_MODEL')


def get_product_line_model():
    """Returns the ProductLine model that is active in this project."""
    return get_concrete_model('BILLING_PRODUCT_LINE_MODEL')


def get_quote_model():
    """Returns the Quote model that is active in this project."""
    return get_concrete_model('BILLING_QUOTE_MODEL')


def get_sales_order_model():
    """Returns the SalesOrder model that is active in this project."""
    return get_concrete_model('BILLING_SALES_ORDER_MODEL')


def get_service_line_model():
    """Returns the ServiceLine model that is active in this project."""
    return get_concrete_model('BILLING_SERVICE_LINE_MODEL')


def get_template_base_model():
    """Returns the TemplateBase model that is active in this project."""
    return get_concrete_model('BILLING_TEMPLATE_BASE_MODEL')
