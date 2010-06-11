# -*- coding: utf-8 -*-

from django.contrib import admin

from products.models import *


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description', 'quantity_per_unit', 'unit_price', 'category', 'sub_category', 'weight', 'stock', 'web_site')
    list_filter = ['sub_category']
    search_fields = ['name']


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'reference', 'category', 'countable', 'unit', 'quantity_per_unit', 'unit_price', 'web_site')
    list_filter = ['category']
    search_fields = ['name']

register = admin.site.register

register(Category)
register(SubCategory)
register(Product, ProductAdmin)

register(ServiceCategory)
register(Service, ServiceAdmin)
