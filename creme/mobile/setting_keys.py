# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

LOCATION_MAP_URL = SettingKey(
    id='mobile-location_map_url',
    description=_(
        "Url pattern to map & geolocation services."
        "Use {search} placeholder for the address (e.g: 'www.google.com/maps?q={search}')."
        "If geolocation is enabled, {lat} & {lng} coordinates can be used too."
    ),
    app_label='mobile',
    type=SettingKey.STRING,
)
