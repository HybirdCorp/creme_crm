# -*- coding: utf-8 -*-

from functools import partial

from creme.creme_core.core.setting_key import SettingKey

from .constants import (MAPI_SERVER_URL, MAPI_DOMAIN, MAPI_SERVER_SSL,
        USER_MOBILE_SYNC_SERVER_URL, USER_MOBILE_SYNC_SERVER_DOMAIN, USER_MOBILE_SYNC_SERVER_SSL,
        USER_MOBILE_SYNC_SERVER_LOGIN, USER_MOBILE_SYNC_SERVER_PWD,
        USER_MOBILE_SYNC_ACTIVITIES, USER_MOBILE_SYNC_CONTACTS)


build_skey = partial(SettingKey, description='', app_label='activesync',
                     type=SettingKey.STRING, hidden=True,
                    )
mapi_server_url_key = build_skey(id=MAPI_SERVER_URL)
mapi_domain_key     = build_skey(id=MAPI_DOMAIN)
mapi_server_ssl_key = build_skey(id=MAPI_SERVER_SSL, type=SettingKey.BOOL)

skeys = (
    mapi_server_url_key,
    mapi_domain_key,
    mapi_server_ssl_key,
    build_skey(id=USER_MOBILE_SYNC_SERVER_URL),
    build_skey(id=USER_MOBILE_SYNC_SERVER_DOMAIN),
    build_skey(id=USER_MOBILE_SYNC_SERVER_SSL, type=SettingKey.BOOL),
    build_skey(id=USER_MOBILE_SYNC_SERVER_LOGIN),
    build_skey(id=USER_MOBILE_SYNC_SERVER_PWD),
    build_skey(id=USER_MOBILE_SYNC_ACTIVITIES, type=SettingKey.BOOL),
    build_skey(id=USER_MOBILE_SYNC_CONTACTS, type=SettingKey.BOOL),
)