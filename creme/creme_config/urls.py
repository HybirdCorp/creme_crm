# -*- coding: utf-8 -*-

from django.urls import include, re_path

from .views import (
    bricks,
    button_menu,
    creme_property_type,
    custom_field,
    custom_form,
    entity_filter,
    fields_config,
    generics_views,
    header_filter,
    history,
    menu,
    portal,
    relation_type,
    search,
    setting,
    transfer,
    user,
    user_role,
    user_settings,
)

user_patterns = [
    re_path(
        r'^portal[/]?$',
        user.Portal.as_view(),
        name='creme_config__users',
    ),
    re_path(
        r'^add[/]?$',
        user.UserCreation.as_view(),
        name='creme_config__create_user',
    ),
    re_path(
        r'^edit/(?P<user_id>\d+)[/]?$',
        user.UserEdition.as_view(),
        name='creme_config__edit_user',
    ),
    re_path(
        r'^activate/(?P<user_id>\d+)[/]?$',
        user.UserActivation.as_view(),
        name='creme_config__activate_user',
    ),
    re_path(
        r'^deactivate/(?P<user_id>\d+)[/]?$',
        user.UserDeactivation.as_view(),
        name='creme_config__deactivate_user',
    ),
    re_path(
        r'^delete/(?P<user_id>\d+)[/]?$',
        user.UserDeletion.as_view(),
        name='creme_config__delete_user',
    ),
    re_path(
        r'^edit/password/(?P<user_id>\d+)[/]?$',
        user.PasswordChange.as_view(),
        name='creme_config__change_user_password',
    ),

    re_path(
        r'^bricks/hide_inactive[/]?$',
        user.HideInactiveUsers.as_view(),
        name='creme_config__users_brick_hide_inactive',
    ),
]

team_patterns = [
    re_path(
        r'^add[/]?$',
        user.TeamCreation.as_view(),
        name='creme_config__create_team',
    ),
    re_path(
        r'^edit/(?P<user_id>\d+)[/]?$',
        user.TeamEdition.as_view(),
        name='creme_config__edit_team',
    ),
]

user_settings_patterns = [
    re_path(
        r'^portal[/]?$',
        user_settings.UserSettings.as_view(),
        name='creme_config__user_settings',
    ),
    re_path(
        r'^set_theme[/]?$',
        user_settings.ThemeSetting.as_view(),
        name='creme_config__set_user_theme',
    ),
    re_path(
        r'^set_timezone[/]?$',
        user_settings.TimeZoneSetting.as_view(),
        name='creme_config__set_user_timezone',
    ),
    re_path(
        r'^set_language[/]?$',
        user_settings.LanguageSetting.as_view(),
        name='creme_config__set_user_language',
    ),
    re_path(
        r'^edit_value/(?P<skey_id>[\w-]+)[/]?$',
        user_settings.UserSettingValueEdition.as_view(),
        name='creme_config__edit_user_setting',
    ),
]

role_patterns = [
    re_path(
        r'^portal[/]?$',
        user_role.Portal.as_view(),
        name='creme_config__roles',
    ),

    re_path(
        r'^wizard[/]?$',
        user_role.RoleCreationWizard.as_view(),
        name='creme_config__create_role',
    ),
    re_path(
        r'^wizard/(?P<role_id>\d+)[/]?$',
        user_role.RoleEditionWizard.as_view(),
        name='creme_config__edit_role',
    ),
    re_path(
        r'^delete/(?P<role_id>\d+)[/]?$',
        user_role.RoleDeletion.as_view(),
        name='creme_config__delete_role',
    ),

    re_path(
        r'^add_credentials/(?P<role_id>\d+)[/]?$',
        user_role.CredentialsAddingWizard.as_view(),
        name='creme_config__add_credentials_to_role',
    ),
    re_path(
        r'^edit_credentials/(?P<cred_id>\d+)[/]?$',
        user_role.CredentialsEditionWizard.as_view(),
        name='creme_config__edit_role_credentials',
    ),
    re_path(
        r'^delete_credentials[/]?$',
        user_role.CredentialsDeletion.as_view(),
        name='creme_config__remove_role_credentials',
    ),
]

relation_type_patterns = [
    re_path(
        r'^portal[/]?$',
        relation_type.Portal.as_view(),
        name='creme_config__rtypes',
    ),

    re_path(
        r'^add[/]?$',
        relation_type.RelationTypeCreation.as_view(),
        name='creme_config__create_rtype',
    ),
    re_path(
        r'^edit/(?P<rtype_id>[\w-]+)[/]?$',
        relation_type.RelationTypeEdition.as_view(),
        name='creme_config__edit_rtype',
    ),
    re_path(
        r'^delete[/]?$',
        relation_type.RelationTypeDeletion.as_view(),
        name='creme_config__delete_rtype',
    ),

    re_path(
        r'^semi_fixed/add[/]?$',
        relation_type.SemiFixedRelationTypeCreation.as_view(),
        name='creme_config__create_semifixed_rtype',
    ),
    re_path(
        r'^semi_fixed/delete[/]?$',
        relation_type.SemiFixedRelationTypeDeletion.as_view(),
        name='creme_config__delete_semifixed_rtype',
    ),
]

property_type_patterns = [
    re_path(
        r'^portal[/]?$',
        creme_property_type.Portal.as_view(),
        name='creme_config__ptypes',
    ),
    re_path(
        r'^add[/]?$',
        creme_property_type.PropertyTypeCreation.as_view(),
        name='creme_config__create_ptype',
    ),
    re_path(
        r'^edit/(?P<ptype_id>[\w-]+)[/]?$',
        creme_property_type.PropertyTypeEdition.as_view(),
        name='creme_config__edit_ptype',
    ),

    re_path(
        r'^enable/(?P<ptype_id>[\w-]+)[/]?$',
        creme_property_type.PropertyTypeEnabling.as_view(),
        name='creme_config__enable_ptype',
    ),
    re_path(
        r'^disable/(?P<ptype_id>[\w-]+)[/]?$',
        creme_property_type.PropertyTypeEnabling.as_view(),
        {'enabled': False},
        name='creme_config__disable_ptype',
    ),
]

fields_config_patterns = [
    re_path(
        r'^portal[/]?$',
        fields_config.Portal.as_view(),
        name='creme_config__fields',
    ),
    re_path(
        r'^wizard[/]?$',
        fields_config.FieldsConfigWizard.as_view(),
        name='creme_config__create_fields_config',
    ),
    re_path(
        r'^edit/(?P<fconf_id>\d+)[/]?$',
        fields_config.FieldsConfigEdition.as_view(),
        name='creme_config__edit_fields_config',
    ),
    re_path(
        r'^delete[/]?$',
        fields_config.FieldsConfigDeletion.as_view(),
        name='creme_config__delete_fields_config',
    ),
]

custom_fields_patterns = [
    re_path(
        r'^portal[/]?$',
        custom_field.Portal.as_view(),
        name='creme_config__custom_fields',
    ),

    re_path(
        r'^ct/add[/]?$',
        custom_field.FirstCTypeCustomFieldCreation.as_view(),
        name='creme_config__create_first_ctype_custom_field',
    ),

    re_path(
        r'^add/(?P<ct_id>\d+)[/]?$',
        custom_field.CustomFieldCreation.as_view(),
        name='creme_config__create_custom_field',
    ),
    re_path(
        r'^edit/(?P<field_id>\d+)[/]?$',
        custom_field.CustomFieldEdition.as_view(),
        name='creme_config__edit_custom_field',
    ),
    re_path(
        r'^delete[/]?$',
        custom_field.CustomFieldDeletion.as_view(),
        name='creme_config__delete_custom_field',
    ),
    re_path(
        r'^restore[/]?$',
        custom_field.CustomFieldRestoration.as_view(),
        name='creme_config__restore_custom_field',
    ),

    re_path(
        r'^bricks/hide_deleted[/]?$',
        custom_field.HideDeletedCustomFields.as_view(),
        name='creme_config__custom_fields_brick_hide_deleted',
    ),

    # Enums
    re_path(
        r'^enum/(?P<field_id>\d+)[/]?$',
        custom_field.CustomEnumsDetail.as_view(),
        name='creme_config__custom_enums',
    ),
    re_path(
        r'^enum/add/widget/(?P<field_id>\d+)[/]?$',
        custom_field.FromWidgetCustomEnumAdding.as_view(),
        name='creme_config__add_custom_enum',
    ),
    re_path(
        r'^enum/add/multi/(?P<field_id>\d+)[/]?$',
        custom_field.CustomEnumsAdding.as_view(),
        name='creme_config__add_custom_enums',
    ),
    re_path(
        r'^enum/edit/(?P<enum_id>\d+)[/]?$',
        custom_field.CustomEnumEdition.as_view(),
        name='creme_config__edit_custom_enum',
    ),
    re_path(
        r'^enum/delete/(?P<enum_id>\d+)[/]?$',
        custom_field.CustomEnumDeletion.as_view(),
        name='creme_config__delete_custom_enum',
    ),
    re_path(
        r'^enum/reload/(?P<field_id>\d+)[/]?$',
        custom_field.CustomEnumBrickReloading.as_view(),
        name='creme_config__reload_custom_enum_brick',
    ),
]

custom_forms_patterns = [
    re_path(
        r'^portal[/]?$',
        custom_form.Portal.as_view(),
        name='creme_config__custom_forms',
    ),

    re_path(
        r'^add/form/(?P<desc_id>.+)[/]?$',
        custom_form.CustomFormCreation.as_view(),
        name='creme_config__create_custom_form',
    ),
    re_path(
        r'^delete/form[/]?$',
        custom_form.CustomFormBrickDeletion.as_view(),
        name='creme_config__delete_custom_form',
    ),

    re_path(
        # r'^add/group/(?P<form_id>.+)[/]?$',
        r'^add/group/(?P<item_id>\d+)[/]?$',
        custom_form.CustomFormGroupCreation.as_view(),
        name='creme_config__add_custom_form_group',
    ),
    re_path(
        # r'^add/extra_group/(?P<form_id>.+)[/]?$',
        r'^add/extra_group/(?P<item_id>\d+)[/]?$',
        custom_form.CustomFormExtraGroupCreation.as_view(),
        name='creme_config__add_custom_form_extra_group',
    ),
    re_path(
        # r'^edit/group/(?P<form_id>.+)/(?P<group_id>\d+)[/]?$',
        r'^edit/group/(?P<item_id>\d+)/(?P<group_id>\d+)[/]?$',
        custom_form.CustomFormGroupEdition.as_view(),
        name='creme_config__edit_custom_form_group',
    ),
    re_path(
        # r'^set_layout/group/(?P<form_id>.+)/(?P<group_id>\d+)[/]?$',
        r'^set_layout/group/(?P<item_id>\d+)/(?P<group_id>\d+)[/]?$',
        custom_form.CustomFormGroupLayoutSetting.as_view(),
        name='creme_config__setlayout_custom_form_group',
    ),
    re_path(
        # r'^reorder/group/(?P<form_id>.+)/(?P<group_id>\d+)[/]?$',
        r'^reorder/group/(?P<item_id>\d+)/(?P<group_id>\d+)[/]?$',
        custom_form.CustomFormGroupReordering.as_view(),
        name='creme_config__reorder_custom_form_group',
    ),
    re_path(
        # r'^delete/group/(?P<form_id>.+)[/]?$',
        r'^delete/group/(?P<item_id>\d+)[/]?$',
        custom_form.CustomFormGroupDeletion.as_view(),
        name='creme_config__delete_custom_form_group',
    ),

    re_path(
        # r'^delete/field/(?P<form_id>.+)[/]?$',
        r'^delete/field/(?P<item_id>\d+)[/]?$',
        custom_form.CustomFormCellDeletion.as_view(),
        name='creme_config__delete_custom_form_cell',
    ),

    re_path(
        r'^brick/expand[/]?$',
        custom_form.CustomFormShowDetails.as_view(),
        name='creme_config__customforms_brick_show_details',
    ),
]

bricks_patterns = [
    re_path(
        r'^portal[/]?$', bricks.Portal.as_view(), name='creme_config__bricks',
    ),

    re_path(
        r'^detailview/add/(?P<ct_id>\d+)[/]?$',
        bricks.BrickDetailviewLocationsCreation.as_view(),
        name='creme_config__create_detailviews_bricks',
    ),
    re_path(
        r'^detailview/edit/(?P<ct_id>\d+)/(?P<role>\w+)[/]?$',
        bricks.BrickDetailviewLocationsEdition.as_view(),
        name='creme_config__edit_detailview_bricks',
    ),
    re_path(
        r'^detailview/delete[/]?$',
        bricks.BrickDetailviewLocationsDeletion.as_view(),
        name='creme_config__delete_detailview_bricks',
    ),

    re_path(
        r'^home/add[/]?$',
        bricks.HomeCreation.as_view(),
        name='creme_config__create_home_bricks',
    ),
    re_path(
        r'^home/edit/(?P<role>\w+)[/]?$',
        bricks.HomeEdition.as_view(),
        name='creme_config__edit_home_bricks',
    ),
    re_path(
        r'^home/delete[/]?$',
        bricks.HomeDeletion.as_view(),
        name='creme_config__delete_home_brick',
    ),  # TODO: 'creme_config__delete_home_brickS'

    re_path(
        r'^mypage/edit/default[/]?$',
        bricks.DefaultMyPageEdition.as_view(),
        name='creme_config__edit_default_mypage_bricks',
    ),
    re_path(
        r'^mypage/edit[/]?$',
        bricks.MyPageEdition.as_view(),
        name='creme_config__edit_mypage_bricks',
    ),
    re_path(
        r'^mypage/default/delete[/]?$',
        bricks.DefaultMyPageDeletion.as_view(),
        name='creme_config__delete_default_mypage_bricks',
    ),
    re_path(
        r'^mypage/delete[/]?$',
        bricks.MyPageDeletion.as_view(),
        name='creme_config__delete_mypage_bricks',
    ),

    re_path(
        r'^rtype/add[/]?$',
        bricks.RelationTypeBrickCreation.as_view(),
        name='creme_config__create_rtype_brick',
    ),
    re_path(
        r'^rtype/(?P<rbi_id>\d+)/wizard[/]?$',
        bricks.RelationCTypeBrickWizard.as_view(),
        name='creme_config__add_cells_to_rtype_brick',
    ),
    re_path(
        r'^rtype/(?P<rbi_id>\d+)/edit_ctype/(?P<ct_id>\d+)[/]?$',
        bricks.RelationCTypeBrickEdition.as_view(),
        name='creme_config__edit_cells_of_rtype_brick',
    ),
    re_path(
        r'^rtype/(?P<rbi_id>\d+)/delete_ctype[/]?$',
        bricks.CellsOfRtypeBrickDeletion.as_view(),
        name='creme_config__delete_cells_of_rtype_brick',
    ),
    re_path(
        r'^rtype/delete[/]?$',
        bricks.RelationTypeBrickDeletion.as_view(),
        name='creme_config__delete_rtype_brick',
    ),

    re_path(
        r'^instance/delete[/]?$',
        bricks.InstanceBrickDeletion.as_view(),
        name='creme_config__delete_instance_brick',
    ),

    re_path(
        r'^custom/wizard[/]?$',
        bricks.CustomBrickWizard.as_view(),
        name='creme_config__create_custom_brick',
    ),
    re_path(
        r'^custom/edit/(?P<cbci_id>[-_\w]+)[/]?$',
        bricks.CustomBrickEdition.as_view(),
        name='creme_config__edit_custom_brick',
    ),
    re_path(
        r'^custom/delete[/]?$',
        bricks.CustomBrickDeletion.as_view(),
        name='creme_config__delete_custom_brick',
    ),
]

menu_patterns = [
    re_path(
        r'^portal[/]?$',
        menu.Portal.as_view(),
        name='creme_config__menu',
    ),
    re_path(
        r'^add/container[/]?$',
        menu.ContainerAdding.as_view(),
        name='creme_config__add_menu_container',
    ),
    re_path(
        r'^add/special_level0[/]?$',
        menu.SpecialLevel0Adding.as_view(),
        name='creme_config__add_menu_special_level0',
    ),
    re_path(
        r'^add/special_level1/(?P<entry_id>[\w-]+)[/]?$',
        menu.SpecialLevel1Adding.as_view(),
        name='creme_config__add_menu_special_level1',
    ),
    re_path(
        r'^container/edit/(?P<item_id>\d+)[/]?$',
        menu.ContainerEdition.as_view(),
        name='creme_config__edit_menu_container',
    ),
    re_path(
        r'^delete/level0[/]?$',
        menu.Level0Deletion.as_view(),
        name='creme_config__delete_menu_level0',
    ),
    re_path(
        r'^reorder/level0/(?P<item_id>\d+)[/]?$',
        menu.Level0Reordering.as_view(),
        name='creme_config__reorder_menu_level0',
    ),
]

button_menu_patterns = [
    re_path(
        r'^portal[/]?$',
        button_menu.Portal.as_view(),
        name='creme_config__buttons',
    ),
    re_path(
        r'^wizard[/]?$',
        button_menu.ButtonMenuWizard.as_view(),
        name='creme_config__add_buttons_to_ctype',
    ),
    re_path(
        r'^edit/(?P<ct_id>\d+)[/]?$',
        button_menu.ButtonMenuEdition.as_view(),
        name='creme_config__edit_ctype_buttons',
    ),
    re_path(
        r'^delete[/]?$',
        button_menu.ButtonMenuDeletion.as_view(),
        name='creme_config__delete_ctype_buttons',
    ),
]

search_patterns = [
    re_path(
        r'^portal[/]?$',
        search.Portal.as_view(),
        name='creme_config__search',
    ),
    re_path(
        r'^add/(?P<ct_id>\d+)[/]?$',
        search.SearchConfigCreation.as_view(),
        name='creme_config__create_search_config',
    ),
    re_path(
        r'^edit/(?P<search_config_id>\d+)[/]?$',
        search.SearchConfigEdition.as_view(),
        name='creme_config__edit_search_config',
    ),
    re_path(
        r'^delete[/]?$',
        search.SearchConfigDeletion.as_view(),
        name='creme_config__delete_search_config',
    ),
]

history_patterns = [
    re_path(
        r'^portal[/]?$',
        history.Portal.as_view(),
        name='creme_config__history',
    ),
    re_path(
        r'^add[/]?$',
        history.HistoryConfigCreation.as_view(),
        name='creme_config__create_history_configs',
    ),
    re_path(
        r'^delete[/]?$',
        history.HistoryItemDeletion.as_view(),
        name='creme_config__remove_history_config',
    ),
]

setting_patterns = [
    re_path(
        r'^edit/(?P<svalue_id>\d+)[/]?$',
        setting.SettingValueEdition.as_view(),
        name='creme_config__edit_setting',
    ),
]

entity_filters_patterns = [
    re_path(
        r'^portal[/]?$',
        entity_filter.Portal.as_view(),
        name='creme_config__efilters',
    ),
    re_path(
        r'^add/(?P<ct_id>\d+)[/]?$',
        entity_filter.EntityFilterCreation.as_view(),
        name='creme_config__create_efilter',
    ),
    re_path(
        r'^edit/(?P<efilter_id>.+)[/]?$',
        entity_filter.EntityFilterEdition.as_view(),
        name='creme_config__edit_efilter',
    ),
]

header_filters_patterns = [
    re_path(
        r'^portal[/]?$',
        header_filter.Portal.as_view(),
        name='creme_config__hfilters',
    ),
    re_path(
        r'^add/(?P<ct_id>\d+)[/]?$',
        header_filter.HeaderFilterCreation.as_view(),
        name='creme_config__create_hfilter',
    ),
    re_path(
        r'^edit/(?P<hfilter_id>.+)[/]?$',
        header_filter.HeaderFilterEdition.as_view(),
        name='creme_config__edit_hfilter',
    ),
]

transfer_patterns = [
    re_path(
        r'^export[/]?$', transfer.ConfigExport.as_view(), name='creme_config__transfer_export',
    ),
    re_path(
        r'^import[/]?$', transfer.ConfigImport.as_view(), name='creme_config__transfer_import',
    ),
]

urlpatterns = [
    re_path(r'^$', portal.Portal.as_view(), name='creme_config__portal'),

    # General
    re_path(r'^bricks/',        include(bricks_patterns)),
    re_path(r'^button_menu/',   include(button_menu_patterns)),
    re_path(r'^custom_fields/', include(custom_fields_patterns)),
    re_path(r'^custom_forms/',  include(custom_forms_patterns)),
    re_path(r'^fields/',        include(fields_config_patterns)),
    re_path(r'^history/',       include(history_patterns)),
    re_path(r'^menu/',          include(menu_patterns)),
    re_path(r'^my_settings/',   include(user_settings_patterns)),
    re_path(r'^property_type/', include(property_type_patterns)),
    re_path(r'^relation_type/', include(relation_type_patterns)),
    re_path(r'^search/',        include(search_patterns)),
    re_path(r'^settings/',      include(setting_patterns)),

    # Credentials
    re_path(r'^role/', include(role_patterns)),
    re_path(r'^team/', include(team_patterns)),
    re_path(r'^user/', include(user_patterns)),

    # List-views
    re_path(r'^entity_filters/', include(entity_filters_patterns)),
    re_path(r'^header_filters/', include(header_filters_patterns)),

    re_path(r'^transfer/', include(transfer_patterns)),

    # Generic portal config
    re_path(
        r'^deletor/finish/(?P<job_id>\d+)[/]?$',
        generics_views.DeletorEnd.as_view(),
        name='creme_config__finish_deletor',
    ),
    re_path(
        r'^(?P<app_name>\w+)/portal[/]?$',
        generics_views.AppPortal.as_view(),
        name='creme_config__app_portal',
    ),
    re_path(
        r'^(?P<app_name>\w+)/reload[/]?$',
        generics_views.AppBricksReloading.as_view(),
        name='creme_config__reload_app_bricks',
    ),
    re_path(
        r'^(?P<app_name>\w+)/(?P<model_name>\w+)/',
        include([
            re_path(
                r'^portal[/]?$',
                generics_views.ModelPortal.as_view(),
                name='creme_config__model_portal',
            ),
            re_path(
                r'^add[/]?$',
                generics_views.GenericCreation.as_view(),
                name='creme_config__create_instance',
            ),
            re_path(
                r'^add_widget[/]?$',
                generics_views.FromWidgetCreation.as_view(),
                name='creme_config__create_instance_from_widget',
            ),
            re_path(
                r'^edit/(?P<object_id>[\w-]+)[/]?$',
                generics_views.GenericEdition.as_view(),
                name='creme_config__edit_instance',
            ),
            re_path(
                r'^(?P<object_id>[\w-]+)/reorder[/]?$',
                generics_views.Reorder.as_view(),
                name='creme_config__reorder_instance',
            ),
            re_path(
                r'^delete/(?P<object_id>[\w-]+)[/]?$',
                generics_views.GenericDeletion.as_view(),
                name='creme_config__delete_instance',
            ),
            re_path(
                r'^reload[/]?$',
                generics_views.ModelBrickReloading.as_view(),
                name='creme_config__reload_model_brick',
            ),
        ])
    ),
]
