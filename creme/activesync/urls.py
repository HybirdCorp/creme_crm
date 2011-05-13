# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('activesync.views',
#    (r'^$', 'portal.portal'),

    (r'^user_settings$', 'user_settings.edit_own_mobile_settings'),

    (r'^sync$', 'sync.main_sync'),

    #Mobile synchronization configuration
    (r'^mobile_synchronization/edit$',    'mobile_sync.edit'),

)

