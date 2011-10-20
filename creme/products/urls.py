# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('products.views',
    (r'^$', 'portal.portal'),

    (r'^products$',                         'product.listview'),
    (r'^product/add$',                      'product.add'),
    (r'^product/edit/(?P<product_id>\d+)$', 'product.edit'),
    (r'^product/(?P<product_id>\d+)$',      'product.detailview'),
    (r'^sub_category/(?P<category_id>\d+)/json$', 'product.get_subcategories'),

    (r'^services$',                         'service.listview'),
    (r'^service/add$',                      'service.add'),
    (r'^service/edit/(?P<service_id>\d+)$', 'service.edit'),
    (r'^service/(?P<service_id>\d+)$',      'service.detailview'),

)
