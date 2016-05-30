# -*- coding: utf-8 -*-

from django.conf.urls import url, include

from .views import (blocks, button_menu, creme_property_type, custom_fields,
        fields_config, generics_views, history, portal, prefered_menu,
        relation_type, search, setting, user, user_role, user_settings,
       )


user_patterns = [
    url(r'^portal/$',                        user.portal),
    url(r'^add/$',                           user.add),
    url(r'^edit/(?P<user_id>\d+)$',          user.edit),
    url(r'^activate/(?P<user_id>\d+)$',      user.activate),
    url(r'^deactivate/(?P<user_id>\d+)$',    user.deactivate),
    url(r'^delete/(?P<user_id>\d+)$',        user.delete),
    url(r'^edit/password/(?P<user_id>\d+)$', user.change_password),
]

team_patterns = [
    url(r'^add/$',                  user.add_team),
    url(r'^edit/(?P<user_id>\d+)$', user.edit_team),
]

user_settings_patterns = [
    url(r'^set_theme/$',                     user_settings.set_theme),
    url(r'^set_timezone/$' ,                 user_settings.set_timezone),
    url(r'^edit_value/(?P<skey_id>[\w-]+)$', user_settings.edit_setting_value),
    url(r'^$',                               user_settings.view),
]

role_patterns = [
    url(r'^portal/$',                          user_role.portal),
    url(r'^add/$',                             user_role.add),
    url(r'^edit/(?P<role_id>\d+)$',            user_role.edit),
    url(r'^delete/(?P<role_id>\d+)$',          user_role.delete),
    url(r'^add_credentials/(?P<role_id>\d+)$', user_role.add_credentials),
    url(r'^delete_credentials$',               user_role.delete_credentials),
]

relation_type_patterns = [
    url(r'^portal/$',                           relation_type.portal),
    url(r'^add/$',                              relation_type.add),
    url(r'^edit/(?P<relation_type_id>[\w-]+)$', relation_type.edit),
    url(r'^delete$',                            relation_type.delete),
    url(r'^semi_fixed/add/$',                   relation_type.add_semi_fixed),
    url(r'^semi_fixed/delete$',                 relation_type.delete_semi_fixed),
]

property_type_patterns = [
    url(r'^portal/$',                           creme_property_type.portal),
    url(r'^add/$',                              creme_property_type.add),
    url(r'^edit/(?P<property_type_id>[\w-]+)$', creme_property_type.edit),
    url(r'^delete$',                            creme_property_type.delete),
]

fields_config_patterns = [
    url(r'^portal/$',                fields_config.portal),
    url(r'^add/$',                   fields_config.add),
    url(r'^edit/(?P<fconf_id>\d+)$', fields_config.edit),
    url(r'^delete$',                 fields_config.delete),
]

custom_fields_patterns = [
    url(r'^portal/$',                custom_fields.portal),
    url(r'^ct/add/$',                custom_fields.add_ct),
    url(r'^ct/(?P<ct_id>\d+)$',      custom_fields.view),
    url(r'^ct/delete$',              custom_fields.delete_ct),
    url(r'^add/(?P<ct_id>\d+)$',     custom_fields.add),
    url(r'^edit/(?P<field_id>\d+)$', custom_fields.edit),
    url(r'^delete$',                 custom_fields.delete),
    url(r'^(?P<ct_id>\d+)/reload/$', custom_fields.reload_block),
]

blocks_patterns = [
    url(r'^portal/$', blocks.portal),

    url(r'^detailview/add/(?P<ct_id>\d+)$',                blocks.add_detailview),
    url(r'^detailview/edit/(?P<ct_id>\d+)/(?P<role>\w+)$', blocks.edit_detailview),
    url(r'^detailview/delete$',                            blocks.delete_detailview),

    url(r'^portal/add/$',                   blocks.add_portal),
    url(r'^portal/edit/(?P<app_name>\w+)$', blocks.edit_portal),
    url(r'^portal/delete$',                 blocks.delete_portal),

    url(r'^mypage/edit/default$',   blocks.edit_default_mypage),
    url(r'^mypage/edit$',           blocks.edit_mypage),
    url(r'^mypage/default/delete$', blocks.delete_default_mypage),
    url(r'^mypage/delete$',         blocks.delete_mypage),

    url(r'^relation_block/add/$',                                      blocks.add_relation_block),
    url(r'^relation_block/add_ctypes/(?P<rbi_id>\d+)$',                blocks.add_ctypes_2_relation_block),
    url(r'^relation_block/(?P<rbi_id>\d+)/edit_ctype/(?P<ct_id>\d+)$', blocks.edit_ctype_of_relation_block),
    url(r'^relation_block/(?P<rbi_id>\d+)/delete_ctype$',              blocks.delete_ctype_of_relation_block),
    url(r'^relation_block/delete$',                                    blocks.delete_relation_block),

    url(r'^instance_block/delete$', blocks.delete_instance_block),

    url(r'^custom/add/$',                      blocks.add_custom_block),
    url(r'^custom/edit/(?P<cbci_id>[-_\w]+)$', blocks.edit_custom_block),
    url(r'^custom/delete$',                    blocks.delete_custom_block),
]

prefered_menu_patterns = [
    url(r'^edit/$',      prefered_menu.edit),
    url(r'^mine/edit/$', prefered_menu.edit_mine),
]

button_menu_patterns = [
    url(r'^portal/$',             button_menu.portal),
    url(r'^add/$',                button_menu.add),
    url(r'^edit/(?P<ct_id>\d+)$', button_menu.edit),
    url(r'^delete$',              button_menu.delete),
]

search_patterns = [
    url(r'^portal/$',                        search.portal),
    url(r'^add/(?P<ct_id>\d+)$',             search.add),
    url(r'^edit/(?P<search_config_id>\d+)$', search.edit),
    url(r'^delete$',                         search.delete),
]

history_patterns = [
    url(r'^portal/$', history.portal),
    url(r'^add/$',    history.add),
    url(r'^delete$',  history.delete),
]

setting_patterns = [
    url(r'^edit/(?P<svalue_id>\d+)$',   setting.edit),
    url(r'^(?P<app_name>\w+)/reload/$', setting.reload_block),
]

urlpatterns = [
    url(r'^$',              portal.portal),
    url(r'^user/',          include(user_patterns)),
    url(r'^team/',          include(team_patterns)),
    url(r'^my_settings/',   include(user_settings_patterns)),
    url(r'^role/',          include(role_patterns)),
    url(r'^relation_type/', include(relation_type_patterns)),
    url(r'^property_type/', include(property_type_patterns)),
    url(r'^fields/',        include(fields_config_patterns)),
    url(r'^custom_fields/', include(custom_fields_patterns)),
    url(r'^blocks/',        include(blocks_patterns)),
    url(r'^prefered_menu/', include(prefered_menu_patterns)),
    url(r'^button_menu/',   include(button_menu_patterns)),
    url(r'^search/',        include(search_patterns)),
    url(r'^history/',       include(history_patterns)),
    url(r'^settings/',      include(setting_patterns)),

    # Generic portal config
    url(r'^models/(?P<ct_id>\d+)/reload/$',                                    generics_views.reload_block),
    url(r'^(?P<app_name>\w+)/portal/$',                                        generics_views.portal_app),
    url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/portal/$',                    generics_views.portal_model),
    url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/add/$',                       generics_views.add_model),
    url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/add_widget/$',                generics_views.add_model_from_widget),
    url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/edit/(?P<object_id>[\w-]+)$', generics_views.edit_model),
    url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/down/(?P<object_id>[\w-]+)$', generics_views.swap_order, {'offset': 1}),
    url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/up/(?P<object_id>[\w-]+)$',   generics_views.swap_order, {'offset': -1}),
    url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/delete$',                     generics_views.delete_model),
]
