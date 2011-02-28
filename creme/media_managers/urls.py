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
