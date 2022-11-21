from django.utils.translation import gettext_lazy as _

from creme import products
from creme.creme_core.gui.custom_form import (
    CustomFormDefault,
    CustomFormDescriptor,
)
from creme.products.forms.base import SubCategorySubCell

Product = products.get_product_model()
Service = products.get_service_model()


class _BaseFormDefault(CustomFormDefault):
    sub_cells = {
        'sub_category': SubCategorySubCell,
    }


# ------------------------------------------------------------------------------
class ProductCreationFormDefault(_BaseFormDefault):
    main_fields = [
        'user',
        'name',
        'code',
        'sub_category',
        'unit_price',
        'unit',
        'quantity_per_unit',
        'weight',
        'stock',
        'web_site',
        'images',  # <=
    ]


class ProductEditionFormDefault(_BaseFormDefault):
    main_fields = [
        'user',
        'name',
        'code',
        'sub_category',
        'unit_price',
        'unit',
        'quantity_per_unit',
        'weight',
        'stock',
        'web_site',
    ]


PRODUCT_CREATION_CFORM = CustomFormDescriptor(
    id='products-product_creation',
    model=Product,
    verbose_name=_('Creation form for product'),
    excluded_fields=('category', 'sub_category'),
    extra_sub_cells=[SubCategorySubCell(model=Product)],
    default=ProductCreationFormDefault,
)
PRODUCT_EDITION_CFORM = CustomFormDescriptor(
    id='products-product_edition',
    model=Product,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for product'),
    excluded_fields=('category', 'sub_category', 'images'),
    extra_sub_cells=[SubCategorySubCell(model=Product)],
    default=ProductEditionFormDefault,
)


# ------------------------------------------------------------------------------
class ServiceCreationFormDefault(_BaseFormDefault):
    main_fields = [
        'user',
        'name',
        'reference',
        'sub_category',
        'images',  # <=
        'countable',
        'unit',
        'quantity_per_unit',
        'unit_price',
        'web_site',
    ]


class ServiceEditionFormDefault(_BaseFormDefault):
    main_fields = [
        'user',
        'name',
        'reference',
        'sub_category',
        'countable',
        'unit',
        'quantity_per_unit',
        'unit_price',
        'web_site',
    ]


SERVICE_CREATION_CFORM = CustomFormDescriptor(
    id='products-service_creation',
    model=Service,
    verbose_name=_('Creation form for service'),
    excluded_fields=('category', 'sub_category'),
    extra_sub_cells=[SubCategorySubCell(model=Service)],
    default=ServiceCreationFormDefault,
)
SERVICE_EDITION_CFORM = CustomFormDescriptor(
    id='products-service_edition',
    model=Service,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for service'),
    excluded_fields=('category', 'sub_category', 'images'),
    extra_sub_cells=[SubCategorySubCell(model=Service)],
    default=ServiceEditionFormDefault,
)

del Product
del Service
