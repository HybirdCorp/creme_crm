# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('activities.views',
    (r'^$', 'portal.portal'),

)

