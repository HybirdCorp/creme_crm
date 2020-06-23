# -*- coding: utf-8 -*-

from django.urls import re_path

from creme import products
from creme.creme_core.conf.urls import Swappable, swap_manager

from .views import product, service

urlpatterns = [
    re_path(
        r'^product/(?P<product_id>\d+)/add_images[/]?$',
        product.ImagesAdding.as_view(),
        name='products__add_images_to_product',
    ),
    re_path(
        r'^service/(?P<service_id>\d+)/add_images[/]?$',
        service.ImagesAdding.as_view(),
        name='products__add_images_to_service',
    ),
    re_path(
        r'^images/remove/(?P<entity_id>\d+)[/]?$',
        product.ImageRemoving.as_view(),
        name='products__remove_image',
    ),

    re_path(
        r'^sub_category/(?P<category_id>\d+)/json[/]?$',
        product.get_subcategories,
        name='products__subcategories',
    ),

    *swap_manager.add_group(
        products.product_model_is_custom,
        Swappable(
            re_path(
                r'^products[/]?$',
                product.ProductsList.as_view(),
                name='products__list_products',
            ),
        ),
        Swappable(
            re_path(
                r'^product/add[/]?$',
                product.ProductCreation.as_view(),
                name='products__create_product',
            ),
        ),
        Swappable(
            re_path(
                r'^product/edit/(?P<product_id>\d+)[/]?$',
                product.ProductEdition.as_view(),
                name='products__edit_product',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^product/(?P<product_id>\d+)[/]?$',
                product.ProductDetail.as_view(),
                name='products__view_product',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='products',
    ).kept_patterns(),

    *swap_manager.add_group(
        products.service_model_is_custom,
        Swappable(
            re_path(
                r'^services[/]?$',
                service.ServicesList.as_view(),
                name='products__list_services',
            ),
        ),
        Swappable(
            re_path(
                r'^service/add[/]?$',
                service.ServiceCreation.as_view(),
                name='products__create_service',
            ),
        ),
        Swappable(
            re_path(
                r'^service/edit/(?P<service_id>\d+)[/]?$',
                service.ServiceEdition.as_view(),
                name='products__edit_service',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^service/(?P<service_id>\d+)[/]?$',
                service.ServiceDetail.as_view(),
                name='products__view_service',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='products',
    ).kept_patterns(),
]
