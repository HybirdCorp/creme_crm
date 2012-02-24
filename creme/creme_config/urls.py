# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, include


user_patterns = patterns('creme_config.views.user',
    (r'^portal/$',                        'portal'),
    (r'^add/$',                           'add'),
    (r'^edit/(?P<user_id>\d+)$',          'edit'),
    (r'^delete/(?P<user_id>\d+)$',        'delete'),
    (r'^edit/password/(?P<user_id>\d+)$', 'change_password'),
)

team_patterns = patterns('creme_config.views.user',
    (r'^add/$',                    'add_team'),
    (r'^edit/(?P<user_id>\d+)$',   'edit_team'),
)

user_settings_patterns = patterns('creme_config.views.user_settings',
    (r'^edit_theme/$', 'edit_theme'),
    (r'^$',            'view'),
)

role_patterns = patterns('creme_config.views.user_role',
    (r'^portal/$',                          'portal'),
    (r'^add/$',                             'add'),
    (r'^edit/(?P<role_id>\d+)$',            'edit'),
    (r'^add_credentials/(?P<role_id>\d+)$', 'add_credentials'),
    (r'^delete$',                           'delete'),
    (r'^set_default_creds/$',               'set_default_creds'),
)

relation_type_patterns = patterns('creme_config.views.relation_type',
    (r'^portal/$',                           'portal'),
    (r'^add/$',                              'add'),
    (r'^edit/(?P<relation_type_id>[\w-]+)$', 'edit'),
    (r'^delete$',                            'delete'),
    (r'^semi_fixed/add/$',                   'add_semi_fixed'),
    (r'^semi_fixed/delete$',                 'delete_semi_fixed'),
)

property_type_patterns = patterns('creme_config.views.creme_property_type',
    (r'^portal/$',                           'portal'),
    (r'^add/$',                              'add'),
    (r'^edit/(?P<property_type_id>[\w-]+)$', 'edit'),
    (r'^delete$',                            'delete'),
)

custom_fields_patterns = patterns('creme_config.views.custom_fields',
    (r'^portal/$',                'portal'),
    (r'^ct/add/$',                'add_ct'),
    (r'^ct/(?P<ct_id>\d+)$',      'view'),
    (r'^ct/delete$',              'delete_ct'),
    (r'^add/(?P<ct_id>\d+)$',     'add'),
    (r'^edit/(?P<field_id>\d+)$', 'edit'),
    (r'^delete$',                 'delete'),
    (r'^(?P<ct_id>\d+)/reload/$', 'reload_block'),
)

blocks_patterns = patterns('creme_config.views.blocks',
    (r'^portal/$',                        'portal'),
    (r'^detailview/add/$',                'add_detailview'),
    (r'^detailview/edit/(?P<ct_id>\d+)$', 'edit_detailview'),
    (r'^detailview/delete$',              'delete_detailview'),
    (r'^portal/add/$',                    'add_portal'),
    (r'^portal/edit/(?P<app_name>\w+)$',  'edit_portal'),
    (r'^portal/delete$',                  'delete_portal'),
    (r'^mypage/edit/default$',            'edit_default_mypage'),
    (r'^mypage/edit$',                    'edit_mypage'),
    (r'^mypage/default/delete$',          'delete_default_mypage'),
    (r'^mypage/delete$',                  'delete_mypage'),
    (r'^relation_block/add/$',            'add_relation_block'),
    (r'^relation_block/delete$',          'delete_relation_block'),
    (r'^instance_block/delete$',          'delete_instance_block'),
)

prefered_menu_patterns = patterns('creme_config.views.prefered_menu',
    (r'^edit/$',      'edit'),
    (r'^mine/edit/$', 'edit_mine'),
)

button_menu_patterns = patterns('creme_config.views.button_menu',
    (r'^portal/$',             'portal'),
    (r'^add/$',                'add'),
    (r'^edit/(?P<ct_id>\d+)$', 'edit'),
    (r'^delete$',              'delete'),
)

search_patterns = patterns('creme_config.views.search',
    (r'^portal/$',                        'portal'),
    (r'^add/$',                           'add'),
    (r'^edit/(?P<search_config_id>\d+)$', 'edit'),
    (r'^delete$',                         'delete'),
)

history_patterns = patterns('creme_config.views.history',
    (r'^portal/$', 'portal'),
    (r'^add/$',    'add'),
    (r'^delete$',  'delete'),
)

setting_patterns = patterns('creme_config.views.setting',
    (r'^edit/(?P<svalue_id>\d+)$',   'edit'),
    (r'^(?P<app_name>\w+)/reload/$', 'reload_block'),
)

urlpatterns = patterns('creme_config.views',
    (r'^$',             'portal.portal'),
    (r'^user/',          include(user_patterns)),
    (r'^team/',          include(team_patterns)),
    (r'^my_settings/',   include(user_settings_patterns)),
    (r'^role/',          include(role_patterns)),
    (r'^relation_type/', include(relation_type_patterns)),
    (r'^property_type/', include(property_type_patterns)),
    (r'^custom_fields/', include(custom_fields_patterns)),
    (r'^blocks/',        include(blocks_patterns)),
    (r'^prefered_menu/', include(prefered_menu_patterns)),
    (r'^button_menu/',   include(button_menu_patterns)),
    (r'^search/',        include(search_patterns)),
    (r'^history/',       include(history_patterns)),
    (r'^settings/',      include(setting_patterns)),

    #Generic portal config
    (r'^models/(?P<ct_id>\d+)/reload/$',                                    'generics_views.reload_block'),
    (r'^(?P<app_name>\w+)/portal/$',                                        'generics_views.portal_app'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/portal/$',                    'generics_views.portal_model'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/add/$',                       'generics_views.add_model'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/edit/(?P<object_id>[\w-]+)$', 'generics_views.edit_model'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/down/(?P<object_id>[\w-]+)$', 'generics_views.swap_order', {'offset': 1}),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/up/(?P<object_id>[\w-]+)$',   'generics_views.swap_order', {'offset': -1}),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/delete$',                     'generics_views.delete_model'),
)
