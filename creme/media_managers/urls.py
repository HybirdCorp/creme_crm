# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('media_managers.views',
    (r'^$', 'portal.portal_media_managers'),

    (r'^images$',                        'image.listview'),
    (r'^image/add$',                     'image.add'),
    (r'^image/edit/(?P<image_id>\d+)$',  'image.edit'),
    (r'^image/(?P<image_id>\d+)$',       'image.detailview'),
    (r'^image/popup/(?P<image_id>\d+)$', 'image.popupview'),
)

urlpatterns += patterns('creme_core.views',
    (r'^image/edit_js/$',                                'ajax.edit_js'),
    (r'^image/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'generic.delete_entities_js'),
    (r'^image/delete/(?P<object_id>\d+)$',               'generic.delete_entity'),
)
