# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('products.views',
    (r'^$', 'portal.portal'),

    (r'^products$',                         'product.listview'),
    (r'^product/add$',                      'product.add'),
    (r'^product/edit/(?P<product_id>\d+)$', 'product.edit'),
    (r'^product/(?P<product_id>\d+)$',      'product.detailview'),

    (r'^services$',                         'service.listview'),
    (r'^service/add$',                      'service.add'),
    (r'^service/edit/(?P<service_id>\d+)$', 'service.edit'),
    (r'^service/(?P<service_id>\d+)$',      'service.detailview'),

    (r'^sub_category/load$', 'ajax.get_sub_cat_on_cat_change'),
)

urlpatterns += patterns('creme_core.views',
    #(r'^product/edit_js/$',                                'ajax.edit_js'),
    (r'^product/delete/(?P<object_id>\d+)$',               'generic.delete_entity'),
    #(r'^product/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'generic.delete_entities_js'), #Commented 6 december 2010

    #(r'^service/edit_js/$',                                'ajax.edit_js'),
    (r'^service/delete/(?P<object_id>\d+)$',               'generic.delete_entity'),
    #(r'^service/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'generic.delete_entities_js'), #Commented 6 december 2010
)
