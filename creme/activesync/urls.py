# -*- coding: utf-8 -*-

from django.conf.urls import url

from .views import user_settings, sync, mobile_sync


urlpatterns = [
    url(r'^user_settings[/]?$',               user_settings.edit_own_mobile_settings, name='activesync__user_settings'),
    # url(r'^sync$', sync.main_sync, name='activesync__sync'),
    url(r'^sync[/]?$',                        sync.sync_portal,                       name='activesync__sync'),
    url(r'^sync/reload[/]?$',                 sync.sync_n_reload_bricks,              name='activesync__sync_n_reload_bricks'),
    url(r'^mobile_synchronization/edit[/]?$', mobile_sync.edit,                       name='activesync__edit_mobile_config'),
]
