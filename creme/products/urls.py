# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import product_model_is_custom, service_model_is_custom
from .views import portal, product, service


urlpatterns = [
    url(r'^$', portal.portal),

    url(r'^product/(?P<product_id>\d+)/add_images$',   product.add_images),
    url(r'^service/(?P<service_id>\d+)/add_images$',   service.add_images),
    url(r'^images/remove/(?P<entity_id>\d+)$',         product.remove_image),

    url(r'^sub_category/(?P<category_id>\d+)/json$',   product.get_subcategories),
]

if not product_model_is_custom():
    urlpatterns += [
        url(r'^products$',                         product.listview,   name='products__list_products'),
        url(r'^product/add$',                      product.add,        name='products__create_product'),
        url(r'^product/edit/(?P<product_id>\d+)$', product.edit,       name='products__edit_product'),
        url(r'^product/(?P<product_id>\d+)$',      product.detailview, name='products__view_product'),
    ]

if not product_model_is_custom():
    urlpatterns += [
        url(r'^services$',                         service.listview,   name='products__list_services'),
        url(r'^service/add$',                      service.add,        name='products__create_service'),
        url(r'^service/edit/(?P<service_id>\d+)$', service.edit,       name='products__edit_service'),
        url(r'^service/(?P<service_id>\d+)$',      service.detailview, name='products__view_service'),
    ]
