# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme import products
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.products.forms.base import SubCategorySubCell

Product = products.get_product_model()
Service = products.get_service_model()

PRODUCT_CREATION_CFORM = CustomFormDescriptor(
    id='products-product_creation',
    model=Product,
    verbose_name=_('Creation form for product'),
    excluded_fields=('category', 'sub_category'),
    extra_sub_cells=[SubCategorySubCell(model=Product)],
)
PRODUCT_EDITION_CFORM = CustomFormDescriptor(
    id='products-product_edition',
    model=Product,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for product'),
    excluded_fields=('category', 'sub_category', 'images'),
    extra_sub_cells=[SubCategorySubCell(model=Product)],
)
SERVICE_CREATION_CFORM = CustomFormDescriptor(
    id='products-service_creation',
    model=Service,
    verbose_name=_('Creation form for service'),
    excluded_fields=('category', 'sub_category'),
    extra_sub_cells=[SubCategorySubCell(model=Service)],
)
SERVICE_EDITION_CFORM = CustomFormDescriptor(
    id='products-service_edition',
    model=Service,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for service'),
    excluded_fields=('category', 'sub_category', 'images'),
    extra_sub_cells=[SubCategorySubCell(model=Service)],
)

del Product
del Service
