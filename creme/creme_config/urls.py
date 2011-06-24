# -*- coding: utf-8 -*-

from imp import find_module

from django.conf.urls.defaults import patterns
from django.conf import settings

from creme_config.registry import config_registry


urlpatterns = patterns('creme_config.views',
    (r'^$', 'portal.portal'),

    #Users
    (r'^user/portal/$',                        'user.portal'),
    (r'^user/add/$',                           'user.add'),
    (r'^user/edit/(?P<user_id>\d+)$',          'user.edit'),
    (r'^user/delete/(?P<user_id>\d+)',         'user.assign_user_n_delete', {'is_team': False}),
    (r'^user/edit/password/(?P<user_id>\d+)$', 'user.change_password'),
    (r'^user/edit/settings/$',                 'user.edit_own_settings'),
    (r'^user/view/settings/$',                 'user.view_own_settings'),
    (r'^team/add/$',                           'user.add_team'),
    (r'^team/edit/(?P<user_id>\d+)$',          'user.edit_team'),
    (r'^team/delete/(?P<user_id>\d+)',         'user.assign_user_n_delete', {'is_team': True}),

    #Roles
    (r'^role/portal/$',                          'user_role.portal'),
    (r'^role/add/$',                             'user_role.add'),
    (r'^role/edit/(?P<role_id>\d+)$',            'user_role.edit'),
    (r'^role/add_credentials/(?P<role_id>\d+)$', 'user_role.add_credentials'),
    (r'^role/delete$',                           'user_role.delete'),
    (r'^role/set_default_creds/$',               'user_role.set_default_creds'),

    #Relations Types
    (r'^relation_type/portal/$',                           'relation_type.portal'),
    (r'^relation_type/add/$',                              'relation_type.add'),
    (r'^relation_type/edit/(?P<relation_type_id>[\w-]+)$', 'relation_type.edit'),
    (r'^relation_type/delete$',                            'relation_type.delete'),

    #Property Types
    (r'^property_type/portal/$',                           'creme_property_type.portal'),
    (r'^property_type/add/$',                              'creme_property_type.add'),
    (r'^property_type/edit/(?P<property_type_id>[\w-]+)$', 'creme_property_type.edit'),
    (r'^property_type/delete$',                            'creme_property_type.delete'),

    #Custom fields
    (r'^custom_fields/portal/$',                'custom_fields.portal'),
    (r'^custom_fields/ct/add/$',                'custom_fields.add_ct'),
    (r'^custom_fields/ct/(?P<ct_id>\d+)$',      'custom_fields.view'),
    (r'^custom_fields/ct/delete$',              'custom_fields.delete_ct'),
    (r'^custom_fields/add/(?P<ct_id>\d+)$',     'custom_fields.add'),
    (r'^custom_fields/edit/(?P<field_id>\d+)$', 'custom_fields.edit'),
    (r'^custom_fields/delete$',                 'custom_fields.delete'),
    (r'^custom_fields/(?P<ct_id>\d+)/reload/$', 'custom_fields.reload_block'),

    #Blocks
    (r'^blocks/portal/$',                     'blocks.portal'),
    (r'^blocks/add/$',                        'blocks.add'),
    (r'^blocks/edit/(?P<ct_id>\d+)$',         'blocks.edit'),
    (r'^blocks/edit/(?P<ct_id>\d+)/portal/$', 'blocks.edit_portal'),
    (r'^blocks/delete$',                      'blocks.delete'),
    (r'^relation_block/add/$',                'blocks.add_relation_block'),
    (r'^relation_block/delete$',              'blocks.delete_relation_block'),
    (r'^instance_block/delete$',              'blocks.delete_instance_block'),

    #Prefered Menu
    (r'^prefered_menu/edit/$', 'prefered_menu.edit'),

    #Button Menu
    (r'^button_menu/portal/$',             'button_menu.portal'),
    (r'^button_menu/add/$',                'button_menu.add'),
    (r'^button_menu/edit/(?P<ct_id>\d+)$', 'button_menu.edit'),
    (r'^button_menu/delete$',              'button_menu.delete'),

    #Search
    (r'^search/portal/$',                        'search.portal'),
    (r'^search/add/$',                           'search.add'),
    (r'^search/edit/(?P<search_config_id>\d+)$', 'search.edit'),
    (r'^search/delete$',                         'search.delete'),

    #History
    (r'^history/portal/$', 'history.portal'),
    (r'^history/add/$',    'history.add'),
    (r'^history/delete$',  'history.delete'),

    #Settings
    (r'^setting/edit/(?P<svalue_id>\d+)$',    'setting.edit'),
    (r'^settings/(?P<app_name>\w+)/reload/$', 'setting.reload_block'),

    #Generic portal config
    (r'^models/(?P<ct_id>\d+)/reload/$',                                      'generics_views.reload_block'),
    (r'^(?P<app_name>\w+)/portal/$',                                          'generics_views.portal_app'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/portal/$',                      'generics_views.portal_model'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/add/$',                         'generics_views.add_model'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/edit/(?P<object_id>[\w-]+)$',   'generics_views.edit_model'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/delete$',                       'generics_views.delete_model'),
)

#TODO: use creme_core.utils.imports ???
for app in settings.INSTALLED_APPS:
    try:
        find_module("creme_config_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
    except ImportError, e:
        # there is no app creme_config.py, skip it
        continue
    config_import = __import__("%s.creme_config_register" % app , globals(), locals(), ['to_register', 'blocks_to_register'], -1)
    config_registry.register(*getattr(config_import, "to_register", ()))
    config_registry.register_blocks(*getattr(config_import, "blocks_to_register", ()))


#    if hasattr(config_import, 'blocks_to_register'):
#        config_registry.register_blocks(*config_import.blocks_to_register)
