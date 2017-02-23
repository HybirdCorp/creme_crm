# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import url, include

from .views import (blocks, button_menu, creme_property_type, custom_fields,
        fields_config, generics_views, history, portal, prefered_menu,
        relation_type, search, setting, user, user_role, user_settings,
       )


user_patterns = [
    url(r'^portal/$',                        user.portal,          name='creme_config__users'),
    url(r'^add/$',                           user.add,             name='creme_config__create_user'),
    url(r'^edit/(?P<user_id>\d+)$',          user.edit,            name='creme_config__edit_user'),
    url(r'^activate/(?P<user_id>\d+)$',      user.activate,        name='creme_config__activate_user'),
    url(r'^deactivate/(?P<user_id>\d+)$',    user.deactivate,      name='creme_config__deactivate_user'),
    url(r'^delete/(?P<user_id>\d+)$',        user.delete,          name='creme_config__delete_user'),
    url(r'^edit/password/(?P<user_id>\d+)$', user.change_password, name='creme_config__change_user_password'),
]

team_patterns = [
    url(r'^add/$',                  user.add_team,  name='creme_config__create_team'),
    url(r'^edit/(?P<user_id>\d+)$', user.edit_team, name='creme_config__edit_team'),
]

user_settings_patterns = [
    url(r'^$',                               user_settings.view,               name='creme_config__user_settings'),
    url(r'^set_theme/$',                     user_settings.set_theme,          name='creme_config__set_user_theme'),
    url(r'^set_timezone/$',                  user_settings.set_timezone,       name='creme_config__set_user_timezone'),
    url(r'^edit_value/(?P<skey_id>[\w-]+)$', user_settings.edit_setting_value, name='creme_config__edit_user_setting'),
]

role_patterns = [
    url(r'^portal/$',                           user_role.portal,                           name='creme_config__roles'),
    url(r'^add/$',                              user_role.add,                              name='creme_config__create_role_legacy'),
    url(r'^edit/(?P<role_id>\d+)$',             user_role.edit,                             name='creme_config__edit_role_legacy'),
    url(r'^wizard[/]*$',                        user_role.UserRoleCreationWizard.as_view(), name='creme_config__create_role'),
    url(r'^wizard/(?P<role_id>\d+)$',           user_role.UserRoleEditionWizard.as_view(),  name='creme_config__edit_role'),
    url(r'^delete/(?P<role_id>\d+)$',           user_role.delete,                           name='creme_config__delete_role'),
    url(r'^add_credentials/(?P<role_id>\d+)$',  user_role.add_credentials,                  name='creme_config__add_credentials_to_role'),
    url(r'^edit_credentials/(?P<cred_id>\d+)$', user_role.edit_credentials,                 name='creme_config__edit_role_credentials'),
    url(r'^delete_credentials$',                user_role.delete_credentials,               name='creme_config__remove_role_credentials'),
]

relation_type_patterns = [
    url(r'^portal/$',                           relation_type.portal,            name='creme_config__rtypes'),
    url(r'^add/$',                              relation_type.add,               name='creme_config__create_rtype'),
    url(r'^edit/(?P<relation_type_id>[\w-]+)$', relation_type.edit,              name='creme_config__edit_rtype'),
    url(r'^delete$',                            relation_type.delete,            name='creme_config__delete_rtype'),
    url(r'^semi_fixed/add/$',                   relation_type.add_semi_fixed,    name='creme_config__create_semifixed_rtype'),
    url(r'^semi_fixed/delete$',                 relation_type.delete_semi_fixed, name='creme_config__delete_semifixed_rtype'),
]

property_type_patterns = [
    url(r'^portal/$',                           creme_property_type.portal, name='creme_config__ptypes'),
    url(r'^add/$',                              creme_property_type.add,    name='creme_config__create_ptype'),
    url(r'^edit/(?P<property_type_id>[\w-]+)$', creme_property_type.edit,   name='creme_config__edit_ptype'),
    url(r'^delete$',                            creme_property_type.delete, name='creme_config__delete_ptype'),
]

fields_config_patterns = [
    url(r'^portal/$',                fields_config.portal,                      name='creme_config__fields'),
    url(r'^add/$',                   fields_config.add,                         name='creme_config__create_fields_config_legacy'),
    url(r'^wizard[/]*$',             fields_config.FieldConfigWizard.as_view(), name='creme_config__create_fields_config'),
    url(r'^edit/(?P<fconf_id>\d+)$', fields_config.edit,                        name='creme_config__edit_fields_config'),
    url(r'^delete$',                 fields_config.delete,                      name='creme_config__delete_fields_config'),
]

custom_fields_patterns = [
    url(r'^portal/$',                custom_fields.portal,       name='creme_config__custom_fields'),
    url(r'^ct/add/$',                custom_fields.add_ct,       name='creme_config__create_first_ctype_custom_field'),
    url(r'^ct/(?P<ct_id>\d+)$',      custom_fields.view,         name='creme_config__ctype_custom_fields'),
    url(r'^ct/delete$',              custom_fields.delete_ct,    name='creme_config__delete_ctype_custom_fields'),
    url(r'^add/(?P<ct_id>\d+)$',     custom_fields.add,          name='creme_config__create_custom_field'),
    url(r'^edit/(?P<field_id>\d+)$', custom_fields.edit,         name='creme_config__edit_custom_field'),
    url(r'^delete$',                 custom_fields.delete,       name='creme_config__delete_custom_field'),
    url(r'^(?P<ct_id>\d+)/reload/$', custom_fields.reload_block, name='creme_config__reload_custom_field_block'),
]

blocks_patterns = [
    url(r'^portal/$', blocks.portal, name='creme_config__blocks'),

    url(r'^detailview/add/(?P<ct_id>\d+)$',                blocks.add_detailview,    name='creme_config__create_detailviews_blocks'),
    url(r'^detailview/edit/(?P<ct_id>\d+)/(?P<role>\w+)$', blocks.edit_detailview,   name='creme_config__edit_detailview_blocks'),
    url(r'^detailview/delete$',                            blocks.delete_detailview, name='creme_config__delete_detailview_blocks'),

    url(r'^portal/wizard[/]*$',             blocks.PortalBlockWizard.as_view(), name='creme_config__create_portal_blocks'),
    url(r'^portal/add/$',                   blocks.add_portal,                  name='creme_config__create_portal_blocks_legagcy'),
    url(r'^portal/edit/(?P<app_name>\w+)$', blocks.edit_portal,                 name='creme_config__edit_portal_blocks'),
    url(r'^portal/delete$',                 blocks.delete_portal,               name='creme_config__delete_portal_blocks'),

    url(r'^home/delete$', blocks.delete_home, name='creme_config__delete_home_block'),

    url(r'^mypage/edit/default$',   blocks.edit_default_mypage,   name='creme_config__edit_default_mypage_blocks'),
    url(r'^mypage/edit$',           blocks.edit_mypage,           name='creme_config__edit_mypage_blocks'),
    url(r'^mypage/default/delete$', blocks.delete_default_mypage, name='creme_config__delete_default_mypage_blocks'),
    url(r'^mypage/delete$',         blocks.delete_mypage,         name='creme_config__delete_mypage_blocks'),

    # url(r'^relation_block/wizard[/]*$',                                blocks.RelationBlockWizard.as_view()),
    url(r'^relation_block/add/$',                                      blocks.add_relation_block,                 name='creme_config__create_rtype_block'),
    url(r'^relation_block/(?P<rbi_id>\d+)/wizard[/]*$',                blocks.RelationCTypeBlockWizard.as_view(), name='creme_config__add_cells_to_rtype_block'),
    url(r'^relation_block/add_ctypes/(?P<rbi_id>\d+)$',                blocks.add_ctypes_2_relation_block,        name='creme_config__add_ctype_config_to_rtype_block'),
    url(r'^relation_block/(?P<rbi_id>\d+)/edit_ctype/(?P<ct_id>\d+)$', blocks.edit_ctype_of_relation_block,       name='creme_config__edit_cells_of_rtype_block'),
    url(r'^relation_block/(?P<rbi_id>\d+)/delete_ctype$',              blocks.delete_ctype_of_relation_block,     name='creme_config__delete_cells_of_rtype_block'),
    url(r'^relation_block/delete$',                                    blocks.delete_relation_block,              name='creme_config__delete_rtype_block'),

    url(r'^instance_block/delete$', blocks.delete_instance_block, name='creme_config__delete_instance_block'),

    url(r'^custom/wizard[/]*$',                blocks.CustomBlockWizard.as_view(), name='creme_config__create_custom_block'),
    url(r'^custom/add/$',                      blocks.add_custom_block,            name='creme_config__create_custom_block_legacy'),
    url(r'^custom/edit/(?P<cbci_id>[-_\w]+)$', blocks.edit_custom_block,           name='creme_config__edit_custom_block'),
    url(r'^custom/delete$',                    blocks.delete_custom_block,         name='creme_config__delete_custom_block'),
]

prefered_menu_patterns = [
    url(r'^edit/$',      prefered_menu.edit,      name='creme_config__edit_preferred_menu'),
    url(r'^mine/edit/$', prefered_menu.edit_mine, name='creme_config__edit_my_preferred_menu'),
] if settings.OLD_MENU else []

button_menu_patterns = [
    url(r'^portal/$',             button_menu.portal,                     name='creme_config__buttons'),
    url(r'^wizard[/]*$',          button_menu.ButtonMenuWizard.as_view(), name='creme_config__add_buttons_to_ctype'),
    url(r'^add/$',                button_menu.add,                        name='creme_config__add_buttons_to_ctype_legacy'),
    url(r'^edit/(?P<ct_id>\d+)$', button_menu.edit,                       name='creme_config__edit_ctype_buttons'),
    url(r'^delete$',              button_menu.delete,                     name='creme_config__delete_ctype_buttons'),
]

search_patterns = [
    url(r'^portal/$',                        search.portal, name='creme_config__search'),
    url(r'^add/(?P<ct_id>\d+)$',             search.add,    name='creme_config__create_search_config'),
    url(r'^edit/(?P<search_config_id>\d+)$', search.edit,   name='creme_config__edit_search_config'),
    url(r'^delete$',                         search.delete, name='creme_config__delete_search_config'),
]

history_patterns = [
    url(r'^portal/$', history.portal, name='creme_config__history'),
    url(r'^add/$',    history.add,    name='creme_config__create_history_configs'),
    url(r'^delete$',  history.delete, name='creme_config__remove_history_config'),
]

setting_patterns = [
    url(r'^edit/(?P<svalue_id>\d+)$',   setting.edit,         name='creme_config__edit_setting'),
    url(r'^(?P<app_name>\w+)/reload/$', setting.reload_block, name='creme_config__reload_settings_block'),
]

urlpatterns = [
    url(r'^$',              portal.portal, name='creme_config__portal'),
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
    url(r'^models/(?P<ct_id>\d+)/reload/$', generics_views.reload_block,                name='creme_config__reload_model_block'),
    url(r'^(?P<app_name>\w+)/portal/$',     generics_views.portal_app,                  name='creme_config__app_portal'),
    url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/', include([
        url(r'^portal/$',                    generics_views.portal_model,               name='creme_config__model_portal'),
        url(r'^add/$',                       generics_views.add_model,                  name='creme_config__create_instance'),
        url(r'^add_widget/$',                generics_views.add_model_from_widget,      name='creme_config__create_instance_from_widget'),
        url(r'^edit/(?P<object_id>[\w-]+)$', generics_views.edit_model,                 name='creme_config__edit_instance'),
        url(r'^down/(?P<object_id>[\w-]+)$', generics_views.swap_order, {'offset': 1},  name='creme_config__move_instance_down'),
        url(r'^up/(?P<object_id>[\w-]+)$',   generics_views.swap_order, {'offset': -1}, name='creme_config__move_instance_up'),
        url(r'^delete$',                     generics_views.delete_model,               name='creme_config__delete_instance'),
    ]))
]
