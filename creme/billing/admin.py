# -*- coding: utf-8 -*-

from django.contrib import admin

from models import *


class BillingBaseAdmin(admin.ModelAdmin):
    list_display  = ('name', 'status', 'issuing_date', 'expiration_date', 'discount', 'total_vat', 'total_no_vat')
    list_filter   = ['status', 'issuing_date', 'expiration_date', 'discount',  'total_vat', 'total_no_vat']
    search_fields = ['name', 'status', 'issuing_date', 'expiration_date', 'discount',  'total_vat', 'total_no_vat']

class LineAdmin(admin.ModelAdmin):
    list_display = ('related_item', 'document', 'comment', 'quantity', 'unit_price', 'discount', 'vat', 'total_discount')


register = admin.site.register

register(Invoice, BillingBaseAdmin)
register(InvoiceStatus)

register(Quote, BillingBaseAdmin)
register(QuoteStatus)

register(SalesOrder, BillingBaseAdmin)
register(SalesOrderStatus)

register(ProductLine, LineAdmin)
register(ServiceLine, LineAdmin)
