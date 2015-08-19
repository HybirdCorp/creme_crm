# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.activesync.views import user_settings, sync, mobile_sync


urlpatterns = [
    url(r'^user_settings$', user_settings.edit_own_mobile_settings),
    url(r'^sync$', sync.main_sync),
    url(r'^mobile_synchronization/edit$', mobile_sync.edit),
]
