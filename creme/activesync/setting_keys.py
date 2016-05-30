# -*- coding: utf-8 -*-

from functools import partial

from creme.creme_core.core.setting_key import SettingKey, UserSettingKey

from . import constants


build_skey = partial(SettingKey, description='', app_label='activesync',
                     type=SettingKey.STRING, hidden=True,
                    )
mapi_server_url_key = build_skey(id=constants.MAPI_SERVER_URL)
mapi_domain_key     = build_skey(id=constants.MAPI_DOMAIN)
mapi_server_ssl_key = build_skey(id=constants.MAPI_SERVER_SSL, type=SettingKey.BOOL)

skeys = (
    mapi_server_url_key,
    mapi_domain_key,
    mapi_server_ssl_key,
    # build_skey(id=constants.USER_MOBILE_SYNC_SERVER_URL),
    # build_skey(id=constants.USER_MOBILE_SYNC_SERVER_DOMAIN),
    # build_skey(id=constants.USER_MOBILE_SYNC_SERVER_SSL, type=SettingKey.BOOL),
    # build_skey(id=constants.USER_MOBILE_SYNC_SERVER_LOGIN),
    # build_skey(id=constants.USER_MOBILE_SYNC_SERVER_PWD),
    # build_skey(id=constants.USER_MOBILE_SYNC_ACTIVITIES, type=SettingKey.BOOL),
    # build_skey(id=constants.USER_MOBILE_SYNC_CONTACTS, type=SettingKey.BOOL),
)

# ---------------
# NB: keys hidden so the description will no be visible (so we do not use ugettext_lazy())
#     they are set for testing purposes.
build_user_skey = partial(UserSettingKey, app_label='activesync',
                          type=SettingKey.STRING, hidden=True,
                         )
user_msync_server_url_key    = build_user_skey(id=constants.USER_MOBILE_SYNC_SERVER_URL,
                                               description='URL of the server',
                                              )
user_msync_server_domain_key = build_user_skey(id=constants.USER_MOBILE_SYNC_SERVER_DOMAIN,
                                               description='Domain of the server',
                                              )
user_msync_server_ssl_key    = build_user_skey(id=constants.USER_MOBILE_SYNC_SERVER_SSL,
                                               type=SettingKey.BOOL,
                                               description='Use SSL',
                                              )
user_msync_server_login_key  = build_user_skey(id=constants.USER_MOBILE_SYNC_SERVER_LOGIN,
                                               description='Login',
                                              )
user_msync_server_pwd_key    = build_user_skey(id=constants.USER_MOBILE_SYNC_SERVER_PWD,
                                               description='Password',
                                              )
user_msync_activities_key    = build_user_skey(id=constants.USER_MOBILE_SYNC_ACTIVITIES,
                                               type=SettingKey.BOOL,
                                               description='Synchronise activities?',
                                              )
user_msync_contacts_key      = build_user_skey(id=constants.USER_MOBILE_SYNC_CONTACTS,
                                               type=SettingKey.BOOL,
                                               description='Synchronise contacts?',
                                              )

user_skeys = (
    user_msync_server_url_key,
    user_msync_server_domain_key,
    user_msync_server_ssl_key,
    user_msync_server_login_key,
    user_msync_server_pwd_key,
    user_msync_activities_key,
    user_msync_contacts_key,
)
