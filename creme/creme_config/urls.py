# -*- coding: utf-8 -*-

from imp import find_module

from django.conf.urls.defaults import patterns
from django.conf import settings

from creme_config.registry import config_registry


urlpatterns = patterns('creme_config.views',
    (r'^$', 'portal.portal'),

    #Relations Types
    (r'^relation_type/portal/$',                             'relation_type.portal'),
    (r'^relation_type/add/$',                                'relation_type.add'),
    (r'^relation_type/edit/(?P<relation_type_id>[\w-]+)$',   'relation_type.edit'),
    (r'^relation_type/delete/(?P<relation_type_id>[\w-]+)$', 'relation_type.delete'),
    (r'^relation_types/reload/$',                            'relation_type.reload_block'),

    #Roles
    (r'^roles/portal/$',                 'role.portal'),
    (r'^roles/add/$',                    'role.add'),
    (r'^roles/edit/(?P<role_id>\d*)$',   'role.edit'),
    (r'^roles/delete/(?P<role_id>\d*)$', 'role.delete'),
    (r'^roles/(?P<role_id>\d*)$',        'role.view'),
    (r'^roles/getDirectDescendant/$',    'role.ajax_get_direct_descendant'),

    (r'^roles/entity_credential/add/$',                           'entity_credential.add'),
    (r'^roles/entity_credential/portal/$',                        'entity_credential.portal'),
    (r'^roles/entity_credential/delete/(?P<entity_cred_id>\d+)$', 'entity_credential.delete'),
    (r'^roles/entity_credential/generate_all/$',                  'entity_credential.generate_all_possibilities'),
    (r'^roles/entity_credentials/reload/$',                       'entity_credential.reload_block'),

    (r'^roles/app_credential/portal/$',                     'app_credential.portal'),
    (r'^roles/app_credential/add/$',                        'app_credential.add'),
    (r'^roles/app_credential/delete/(?P<app_cred_id>\d+)$', 'app_credential.delete'),
    (r'^roles/app_credentials/reload/$',                    'app_credential.reload_block'),

    #Profiles
    (r'^profile/portal/$',                    'profile.portal'),
    (r'^profile/add/$',                       'profile.add'),
    (r'^profile/edit/(?P<profile_id>\d*)$',   'profile.edit'),
    (r'^profile/delete/(?P<profile_id>\d*)$', 'profile.delete'),
#    (r'^profile/(?P<profile_id>\d*)$', 'profiles_views.view_profile'),

    #Users
    (r'^user/portal/$',                        'user.portal'),
    (r'^user/add/$',                           'user.add'),
    (r'^user/edit/(?P<user_id>\d*)$',          'user.edit'),
    (r'^user/delete/(?P<user_id>\d*)$',        'user.delete'),
    (r'^user/edit/password/(?P<user_id>\d*)$', 'user.change_password'),
    (r'^user/edit/settings/$',                 'user.edit_own_settings'),
    (r'^users/reload/$',                       'user.reload_block'),

    #Property Types
    (r'^property_type/portal/$',                             'creme_property_type.portal'),
    (r'^property_type/add/$',                                'creme_property_type.add'),
    (r'^property_type/edit/(?P<property_type_id>[\w-]+)$',   'creme_property_type.edit'),
    (r'^property_type/delete/(?P<property_type_id>[\w-]+)$', 'creme_property_type.delete'),
    (r'^property_types/reload/$',                            'creme_property_type.reload_block'),

    #Blocks
    (r'^blocks/portal/$',                     'blocks.portal'),
    (r'^blocks/add/$',                        'blocks.add'),
    (r'^blocks/edit/(?P<ct_id>\d+)$',         'blocks.edit'),
    (r'^blocks/edit/(?P<ct_id>\d+)/portal/$', 'blocks.edit_portal'),
    (r'^blocks/delete/(?P<ct_id>\d+)$',       'blocks.delete'),
    (r'^blocks/reload/$',                     'blocks.reload_block'),

    #Prefered Menu
    (r'^prefered_menu/edit/$', 'prefered_menu.edit'),

    #Button Menu
    (r'^button_menu/portal/$',                'button_menu.portal'),
    (r'^button_menu/add/$',                   'button_menu.add'),
    (r'^button_menu/edit/(?P<ct_id>\d+)$',    'button_menu.edit'),
    (r'^button_menu/delete/(?P<ct_id>\d+)$',  'button_menu.delete'),
    (r'^button_menu/reload/$',                'button_menu.reload_block'),

    #MailSignature
    (r'^mailsignature/portal/$',                          'mail_signature.portal'),
    (r'^mailsignature/add/$',                             'mail_signature.add'),
    (r'^mailsignature/edit/(?P<mailsignature_id>\d*)$',   'mail_signature.edit'),
    (r'^mailsignature/delete/(?P<mailsignature_id>\d*)$', 'mail_signature.delete'),
#    (r'^mailsignature/(?P<mailsignature_id>\d*)$', 'mail_signature_views.view_mailsignature'),

    #Generic portal config
    (r'^models/(?P<ct_id>\d+)/reload/$',                                      'generics_views.reload_block'),
    (r'^(?P<app_name>\w+)/portal/$',                                          'generics_views.portal_app'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/portal/$',                      'generics_views.portal_model'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/add/$',                         'generics_views.add_model'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/edit/(?P<object_id>[\w-]+)$',   'generics_views.edit_model'),
    (r'^(?P<app_name>\w+)/(?P<model_name>\w+)/delete/(?P<object_id>[\w-]+)$', 'generics_views.delete_model'),
)


for app in settings.INSTALLED_APPS:
    try:
        find_module("creme_config_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
    except ImportError, e:
        # there is no app creme_config.py, skip it
        continue
    config_import = __import__("%s.creme_config_register" % app , globals(), locals(), ['to_register'], -1)
    config_registry.register(*config_import.to_register)
