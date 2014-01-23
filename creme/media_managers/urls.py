# -*- coding: utf-8 -*-

from django.conf.urls import patterns


urlpatterns = patterns('creme.media_managers.views',
    (r'^$', 'portal.portal_media_managers'),

    (r'^images$',                          'image.listview'),
    #(r'^images/popup$',                    'image.listview_popup'),
    (r'^images/(?P<image_id>\d+)/get_url', 'image.get_url'), #TODO: 'images' -> 'image' ??

    (r'^tiny_mce/image$',                'image.select_image_tiny_mce'),

    (r'^image/add$',                     'image.add'),
    (r'^image/edit/(?P<image_id>\d+)$',  'image.edit'),
    (r'^image/(?P<image_id>\d+)$',       'image.detailview'),
    #(r'^image/popup/(?P<image_id>\d+)$', 'image.popupview'),
)
