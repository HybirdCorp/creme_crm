# -*- coding: utf-8 -*-

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

LOCATION_MAP_URL = SettingKey(
    id='mobile-location_map_url',
    description=format_lazy((
        '{title}\n'
        ' − https://www.openstreetmap.org/search?query={{search}}\n'
        ' − https://www.openstreetmap.org#map=18/{{lat}}/{{lng}}\n'
        ' − https://www.google.com/maps/?q={{search}}\n'
        ' − https://maps.google.com/maps/place/{{lat}},{{lng}}'
    ), title=_(
        "URL pattern to map & geolocation services.\n"
        "Use {search} placeholder for the address and if geolocation is enabled, "
        "{lat} & {lng} coordinates can be used too."
    )),
    app_label='mobile',
    type=SettingKey.STRING,
)
