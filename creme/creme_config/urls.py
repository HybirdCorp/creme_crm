# -*- coding: utf-8 -*-

# from django.conf.urls import url, include
from django.urls import re_path, include

from .views import (bricks, button_menu, creme_property_type, custom_fields,
        fields_config, generics_views, history, portal,
        relation_type, search, setting, user, user_role, user_settings,
)


user_patterns = [
    re_path(r'^portal[/]?$',                         user.Portal.as_view(),           name='creme_config__users'),
    re_path(r'^add[/]?$',                            user.UserCreation.as_view(),     name='creme_config__create_user'),
    re_path(r'^edit/(?P<user_id>\d+)[/]?$',          user.UserEdition.as_view(),      name='creme_config__edit_user'),
    # re_path(r'^activate/(?P<user_id>\d+)[/]?$',      user.activate,                   name='creme_config__activate_user'),
    re_path(r'^activate/(?P<user_id>\d+)[/]?$',      user.UserActivation.as_view(),   name='creme_config__activate_user'),
    # re_path(r'^deactivate/(?P<user_id>\d+)[/]?$',    user.deactivate,               name='creme_config__deactivate_user'),
    re_path(r'^deactivate/(?P<user_id>\d+)[/]?$',    user.UserDeactivation.as_view(), name='creme_config__deactivate_user'),
    re_path(r'^delete/(?P<user_id>\d+)[/]?$',        user.UserDeletion.as_view(),     name='creme_config__delete_user'),
    re_path(r'^edit/password/(?P<user_id>\d+)[/]?$', user.PasswordChange.as_view(),   name='creme_config__change_user_password'),

    re_path(
        r'^bricks/hide_inactive[/]?$',
        user.HideInactiveUsers.as_view(),
        name='creme_config__users_brick_hide_inactive',
    ),
]

team_patterns = [
    re_path(r'^add[/]?$',                   user.TeamCreation.as_view(), name='creme_config__create_team'),
    re_path(r'^edit/(?P<user_id>\d+)[/]?$', user.TeamEdition.as_view(),  name='creme_config__edit_team'),
]

user_settings_patterns = [
    re_path(r'^portal[/]?$',       user_settings.UserSettings.as_view(),    name='creme_config__user_settings'),
    # url(r'^set_theme[/]?$',    user_settings.set_theme,              name='creme_config__set_user_theme'),
    re_path(r'^set_theme[/]?$',    user_settings.ThemeSetting.as_view(),    name='creme_config__set_user_theme'),
    # url(r'^set_timezone[/]?$', user_settings.set_timezone,           name='creme_config__set_user_timezone'),
    re_path(r'^set_timezone[/]?$', user_settings.TimeZoneSetting.as_view(), name='creme_config__set_user_timezone'),
    re_path(r'^edit_value/(?P<skey_id>[\w-]+)[/]?$',
            user_settings.UserSettingValueEdition.as_view(),
            name='creme_config__edit_user_setting',
    ),
]

role_patterns = [
    re_path(r'^portal[/]?$', user_role.Portal.as_view(), name='creme_config__roles'),

    re_path(r'^wizard[/]?$',                  user_role.RoleCreationWizard.as_view(),  name='creme_config__create_role'),
    re_path(r'^wizard/(?P<role_id>\d+)[/]?$', user_role.RoleEditionWizard.as_view(),   name='creme_config__edit_role'),
    re_path(r'^delete/(?P<role_id>\d+)[/]?$', user_role.RoleDeletion.as_view(),        name='creme_config__delete_role'),

    # re_path(r'^add_credentials/(?P<role_id>\d+)[/]?$', user_role.CredentialsAdding.as_view(), name='creme_config__add_credentials_to_role'),
    re_path(r'^add_credentials/(?P<role_id>\d+)[/]?$',
            user_role.CredentialsAddingWizard.as_view(),
            name='creme_config__add_credentials_to_role',
           ),
    # re_path(r'^edit_credentials/(?P<cred_id>\d+)[/]?$', user_role.CredentialsEdition.as_view(), name='creme_config__edit_role_credentials'),
    re_path(r'^edit_credentials/(?P<cred_id>\d+)[/]?$',
            user_role.CredentialsEditionWizard.as_view(),
            name='creme_config__edit_role_credentials',
           ),
    # re_path(r'^delete_credentials[/]?$', user_role.delete_credentials, name='creme_config__remove_role_credentials'),
    re_path(r'^delete_credentials[/]?$',
            user_role.CredentialsDeletion.as_view(),
            name='creme_config__remove_role_credentials',
           ),
]

relation_type_patterns = [
    re_path(r'^portal[/]?$',                    relation_type.Portal.as_view(),               name='creme_config__rtypes'),
    re_path(r'^add[/]?$',                       relation_type.RelationTypeCreation.as_view(), name='creme_config__create_rtype'),
    re_path(r'^edit/(?P<rtype_id>[\w-]+)[/]?$', relation_type.RelationTypeEdition.as_view(),  name='creme_config__edit_rtype'),
    # re_path(r'^delete[/]?$',                    relation_type.delete,                         name='creme_config__delete_rtype'),
    re_path(r'^delete[/]?$',                    relation_type.RelationTypeDeletion.as_view(), name='creme_config__delete_rtype'),

    re_path(r'^semi_fixed/add[/]?$',
            relation_type.SemiFixedRelationTypeCreation.as_view(),
            name='creme_config__create_semifixed_rtype',
    ),
    re_path(r'^semi_fixed/delete[/]?$',
            # relation_type.delete_semi_fixed,
            relation_type.SemiFixedRelationTypeDeletion.as_view(),
            name='creme_config__delete_semifixed_rtype',
    ),
]

property_type_patterns = [
    re_path(r'^portal[/]?$',                    creme_property_type.Portal.as_view(),               name='creme_config__ptypes'),
    re_path(r'^add[/]?$',                       creme_property_type.PropertyTypeCreation.as_view(), name='creme_config__create_ptype'),
    re_path(r'^edit/(?P<ptype_id>[\w-]+)[/]?$', creme_property_type.PropertyTypeEdition.as_view(),  name='creme_config__edit_ptype'),
    re_path(r'^delete[/]?$',                    creme_property_type.delete,                         name='creme_config__delete_ptype'),
]

fields_config_patterns = [
    # re_path(r'^portal[/]?$',                 fields_config.portal,                        name='creme_config__fields'),
    re_path(r'^portal[/]?$',                 fields_config.Portal.as_view(),               name='creme_config__fields'),
    re_path(r'^wizard[/]?$',                 fields_config.FieldsConfigWizard.as_view(),   name='creme_config__create_fields_config'),
    re_path(r'^edit/(?P<fconf_id>\d+)[/]?$', fields_config.FieldsConfigEdition.as_view(),  name='creme_config__edit_fields_config'),
    # re_path(r'^delete[/]?$',                 fields_config.delete,                        name='creme_config__delete_fields_config'),
    re_path(r'^delete[/]?$',                 fields_config.FieldsConfigDeletion.as_view(), name='creme_config__delete_fields_config'),
]

custom_fields_patterns = [
    re_path(r'^portal[/]?$', custom_fields.Portal.as_view(), name='creme_config__custom_fields'),
    re_path(r'^ct/add[/]?$',
        custom_fields.FirstCTypeCustomFieldCreation.as_view(),
        name='creme_config__create_first_ctype_custom_field',
    ),
    # re_path(r'^ct/delete[/]?$',              custom_fields.delete_ct,                     name='creme_config__delete_ctype_custom_fields'),
    re_path(r'^ct/delete[/]?$',              custom_fields.CTypeCustomFieldsDeletion.as_view(), name='creme_config__delete_ctype_custom_fields'),
    re_path(r'^add/(?P<ct_id>\d+)[/]?$',     custom_fields.CustomFieldCreation.as_view(),       name='creme_config__create_custom_field'),
    re_path(r'^edit/(?P<field_id>\d+)[/]?$', custom_fields.CustomFieldEdition.as_view(),        name='creme_config__edit_custom_field'),
    # re_path(r'^delete[/]?$',                 custom_fields.delete,                        name='creme_config__delete_custom_field'),
    re_path(r'^delete[/]?$',                 custom_fields.CustomFieldDeletion.as_view(),       name='creme_config__delete_custom_field'),
]

bricks_patterns = [
    re_path(r'^portal[/]?$', bricks.Portal.as_view(), name='creme_config__bricks'),

    re_path(r'^detailview/add/(?P<ct_id>\d+)[/]?$',                bricks.BrickDetailviewLocationsCreation.as_view(), name='creme_config__create_detailviews_bricks'),
    re_path(r'^detailview/edit/(?P<ct_id>\d+)/(?P<role>\w+)[/]?$', bricks.BrickDetailviewLocationsEdition.as_view(),  name='creme_config__edit_detailview_bricks'),
    # re_path(r'^detailview/delete[/]?$',                            bricks.delete_detailview,                          name='creme_config__delete_detailview_bricks'),
    re_path(r'^detailview/delete[/]?$',                            bricks.BrickDetailviewLocationsDeletion.as_view(), name='creme_config__delete_detailview_bricks'),

    re_path(r'^home/add[/]?$',                bricks.HomeCreation.as_view(), name='creme_config__create_home_bricks'),
    # url(r'^home/edit[/]?$',   bricks.HomeEdition.as_view(),  name='creme_config__edit_home_bricks'),
    re_path(r'^home/edit/(?P<role>\w+)[/]?$', bricks.HomeEdition.as_view(),  name='creme_config__edit_home_bricks'),
    # re_path(r'^home/delete[/]?$',             bricks.delete_home,            name='creme_config__delete_home_brick'),
    re_path(r'^home/delete[/]?$',             bricks.HomeDeletion.as_view(), name='creme_config__delete_home_brick'),  # TODO: 'creme_config__delete_home_brickS'

    re_path(r'^mypage/edit/default[/]?$',   bricks.DefaultMyPageEdition.as_view(),  name='creme_config__edit_default_mypage_bricks'),
    re_path(r'^mypage/edit[/]?$',           bricks.MyPageEdition.as_view(),         name='creme_config__edit_mypage_bricks'),
    # re_path(r'^mypage/default/delete[/]?$', bricks.delete_default_mypage,          name='creme_config__delete_default_mypage_bricks'),
    re_path(r'^mypage/default/delete[/]?$', bricks.DefaultMyPageDeletion.as_view(), name='creme_config__delete_default_mypage_bricks'),
    # re_path(r'^mypage/delete[/]?$',         bricks.delete_mypage,                   name='creme_config__delete_mypage_bricks'),
    re_path(r'^mypage/delete[/]?$',         bricks.MyPageDeletion.as_view(),        name='creme_config__delete_mypage_bricks'),

    re_path(r'^rtype/add[/]?$',                                       bricks.RelationTypeBrickCreation.as_view(), name='creme_config__create_rtype_brick'),
    re_path(r'^rtype/(?P<rbi_id>\d+)/wizard[/]?$',                    bricks.RelationCTypeBrickWizard.as_view(),  name='creme_config__add_cells_to_rtype_brick'),
    re_path(r'^rtype/(?P<rbi_id>\d+)/edit_ctype/(?P<ct_id>\d+)[/]?$', bricks.RelationCTypeBrickEdition.as_view(), name='creme_config__edit_cells_of_rtype_brick'),
    # re_path(r'^rtype/(?P<rbi_id>\d+)/delete_ctype[/]?$',              bricks.delete_cells_of_rtype_brick,         name='creme_config__delete_cells_of_rtype_brick'),
    re_path(r'^rtype/(?P<rbi_id>\d+)/delete_ctype[/]?$',              bricks.CellsOfRtypeBrickDeletion.as_view(), name='creme_config__delete_cells_of_rtype_brick'),
    # re_path(r'^rtype/delete[/]?$',                                    bricks.delete_rtype_brick,                  name='creme_config__delete_rtype_brick'),
    re_path(r'^rtype/delete[/]?$',                                    bricks.RelationTypeBrickDeletion.as_view(), name='creme_config__delete_rtype_brick'),

    # re_path(r'^instance/delete[/]?$', bricks.delete_instance_brick, name='creme_config__delete_instance_brick'),
    re_path(r'^instance/delete[/]?$', bricks.InstanceBrickDeletion.as_view(), name='creme_config__delete_instance_brick'),

    re_path(r'^custom/wizard[/]?$',                    bricks.CustomBrickWizard.as_view(),   name='creme_config__create_custom_brick'),
    re_path(r'^custom/edit/(?P<cbci_id>[-_\w]+)[/]?$', bricks.CustomBrickEdition.as_view(),  name='creme_config__edit_custom_brick'),
    # re_path(r'^custom/delete[/]?$',                    bricks.delete_custom_brick,          name='creme_config__delete_custom_brick'),
    re_path(r'^custom/delete[/]?$',                    bricks.CustomBrickDeletion.as_view(), name='creme_config__delete_custom_brick'),
]

button_menu_patterns = [
    re_path(r'^portal[/]?$',              button_menu.Portal.as_view(),             name='creme_config__buttons'),
    re_path(r'^wizard[/]?$',              button_menu.ButtonMenuWizard.as_view(),   name='creme_config__add_buttons_to_ctype'),
    re_path(r'^edit/(?P<ct_id>\d+)[/]?$', button_menu.ButtonMenuEdition.as_view(),  name='creme_config__edit_ctype_buttons'),
    # re_path(r'^delete[/]?$',              button_menu.delete,                      name='creme_config__delete_ctype_buttons'),
    re_path(r'^delete[/]?$',              button_menu.ButtonMenuDeletion.as_view(), name='creme_config__delete_ctype_buttons'),
]

search_patterns = [
    re_path(r'^portal[/]?$',                         search.Portal.as_view(),               name='creme_config__search'),
    re_path(r'^add/(?P<ct_id>\d+)[/]?$',             search.SearchConfigCreation.as_view(), name='creme_config__create_search_config'),
    re_path(r'^edit/(?P<search_config_id>\d+)[/]?$', search.SearchConfigEdition.as_view(),  name='creme_config__edit_search_config'),
    # re_path(r'^delete[/]?$',                         search.delete,                         name='creme_config__delete_search_config'),
    re_path(r'^delete[/]?$',                         search.SearchItemEdition.as_view(),    name='creme_config__delete_search_config'),
]

history_patterns = [
    re_path(r'^portal[/]?$',  history.Portal.as_view(),                name='creme_config__history'),
    re_path(r'^add[/]?$',     history.HistoryConfigCreation.as_view(), name='creme_config__create_history_configs'),
    # re_path(r'^delete[/]?$',  history.delete,                          name='creme_config__remove_history_config'),
    re_path(r'^delete[/]?$',  history.HistoryItemDeletion.as_view(),   name='creme_config__remove_history_config'),
]

setting_patterns = [
    re_path(r'^edit/(?P<svalue_id>\d+)[/]?$', setting.SettingValueEdition.as_view(), name='creme_config__edit_setting'),
]

urlpatterns = [
    re_path(r'^$',              portal.Portal.as_view(), name='creme_config__portal'),
    re_path(r'^user/',          include(user_patterns)),
    re_path(r'^team/',          include(team_patterns)),
    re_path(r'^my_settings/',   include(user_settings_patterns)),
    re_path(r'^role/',          include(role_patterns)),
    re_path(r'^relation_type/', include(relation_type_patterns)),
    re_path(r'^property_type/', include(property_type_patterns)),
    re_path(r'^fields/',        include(fields_config_patterns)),
    re_path(r'^custom_fields/', include(custom_fields_patterns)),
    re_path(r'^bricks/',        include(bricks_patterns)),
    re_path(r'^button_menu/',   include(button_menu_patterns)),
    re_path(r'^search/',        include(search_patterns)),
    re_path(r'^history/',       include(history_patterns)),
    re_path(r'^settings/',      include(setting_patterns)),

    # Generic portal config
    re_path(r'^deletor/finish/(?P<job_id>\d+)[/]?$', generics_views.DeletorEnd.as_view(), name='creme_config__finish_deletor'),
    re_path(r'^(?P<app_name>\w+)/portal[/]?$',       generics_views.AppPortal.as_view(),  name='creme_config__app_portal'),
    re_path(r'^(?P<app_name>\w+)/reload[/]?$',       generics_views.reload_app_bricks,    name='creme_config__reload_app_bricks'),
    re_path(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/', include([
        re_path(r'^portal[/]?$',                        generics_views.ModelPortal.as_view(),        name='creme_config__model_portal'),
        re_path(r'^add[/]?$',                           generics_views.GenericCreation.as_view(),    name='creme_config__create_instance'),
        re_path(r'^add_widget[/]?$',                    generics_views.FromWidgetCreation.as_view(), name='creme_config__create_instance_from_widget'),
        re_path(r'^edit/(?P<object_id>[\w-]+)[/]?$',    generics_views.GenericEdition.as_view(),     name='creme_config__edit_instance'),
        re_path(r'^(?P<object_id>[\w-]+)/reorder[/]?$', generics_views.Reorder.as_view(),            name='creme_config__reorder_instance'),
        # re_path(r'^delete[/]?$',                        generics_views.delete_model,                 name='creme_config__delete_instance'),
        re_path(r'^delete/(?P<object_id>[\w-]+)[/]?$',  generics_views.GenericDeletion.as_view(),    name='creme_config__delete_instance'),
        re_path(r'^reload[/]?$',                        generics_views.reload_model_brick,           name='creme_config__reload_model_brick'),
    ])),
]
